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
