# This module is for managing IPFS

import io
import ipfsapi

def mk_links(ipfs, mods):
    """
    Creates IPFS directory links for all of the given mods, then returns a dict
    mapping (filename, hash) pairs to their IPFS paths.
    """
    links = {}
    for _, mod in mods.items():
        for vsn in mod.versions:
            for file in vsn.files:
                if file.ipfs == '': continue
                ipdir = ipfs.object_put(io.BytesIO('''
                {{
                    "Links": [ {{
                        "Name": "{}",
                        "Hash": "{}"
                    }} ]
                }}'''.format(file.filename, file.ipfs).encode('utf-8')))
                links[(file.filename, file.hash_.digest)] = ipdir['Hash'] + '/' + file.filename
    return links

def wanted_pins(mods):
    files = dict()
    for _, mod in mods.items():
        for vsn in mod.versions:
            for file in vsn.files:
                if file.ipfs != '':
                    if file.ipfs not in files:
                        files[file.ipfs] = { 'files': [file.filename] }
                    else:
                        files[file.ipfs]['files'].append(file.filename)
    return files

def pinned_files(ipfs, mods):
    """
    Returns a set of all IPFS hashes in the given mods list which are pinned to
    the node.
    """
    files = wanted_pins(mods)
    pinned = dict()
    for phash, _ in ipfs.pin_ls()['Keys'].items():
        if phash not in files: continue
        stat = ipfs.object_stat(phash)
        pinned[phash] = { 'size': stat['CumulativeSize'], 'files': files[phash]['files'] }
    return pinned

def pin_files(ipfs, mods, callback=None):
    """
    Pins all of the files in the given mod list to the IPFS node. This should
    cause the node to fetch the files and serve them for others to download.
    """
    pinned = set()
    for phash, _ in ipfs.pin_ls()['Keys'].items():
        pinned.add(phash)
    for _, mod in mods.items():
        for vsn in mod.versions:
            for file in vsn.files:
                if file.ipfs != '' and file.ipfs not in pinned:
                    print('Pinning {} ({})'.format(file.ipfs, file.filename))
                    ipfs.pin_add(file.ipfs)
                    if callback: callback(file.ipfs)
