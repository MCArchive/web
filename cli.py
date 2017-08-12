#!/usr/bin/env python

import os.path
from argparse import ArgumentParser
import tempfile
import json
import re
import hashlib
import ipfsapi

import metafile

repo_path = 'repo'

def load_mods(args):
    return metafile.load_mods(os.path.join(repo_path, 'mods'))

def hash_file(path):
    hash_ = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk: break
            hash_.update(chunk)
    return hash_.hexdigest()

def add_json_entry(mod, mfile, field):
    """
    Adds a json field to the given version in the mod file without disturbing
    the file's formatting or field ordering in the file.

    This is done by just inserting a line after the `filename` field.
    """
    fname = os.path.basename(mfile)
    with open(mod, 'r') as f:
        lines = f.readlines()
    name_re = re.compile(r'( *)"filename" *: *"'+fname+r'"(,?)')
    indent_sp = ""
    comma = ""
    idx = -1
    for i, line in enumerate(lines):
        match = name_re.match(line)
        if match:
            idx = i
            indent_sp = match.group(1)
            comma = match.group(2)
    if idx < 0:
        print('Couldn\'t find filename entry for '+mfile)
        return
    lines.insert(idx+1, indent_sp + field + comma + '\n')
    with open(mod, 'w') as f:
        f.writelines(lines)
    print('Added archived field to file')

def find_file_vsn(mod, path):
    vsn = None
    modf = None
    for v in mod.versions:
        for f in v.files:
            if os.path.basename(path) == f.filename:
                vsn = v
                modf = f
                break
    return vsn, modf

def archive_ipfs(args):
    ipfs = ipfsapi.connect()
    mod = metafile.load_mod_file(args.mod)
    for path in args.files:
        vsn, modf = find_file_vsn(mod, path)
        if modf is None:
            print("No version found for file " + path)
            continue
        if modf.ipfs != '':
            print("{} is already in IPFS. Skipping".format(modf.filename))
            continue
        fhash = hash_file(path)
        if fhash != modf.hash_.digest:
            print("Hash mismatch for {}\nExpected:\t{}\nActual:\t{}".format(path, modf.hash_.digest, fhash))
            continue
        result = ipfs.add(path)
        print(result)
        print('Added {}'.format(result['Hash']))
        add_json_entry(args.mod, path, '"ipfs": "' + result['Hash'] + '"')


parser = ArgumentParser(description='A command line interface for managing the archive')
subp = parser.add_subparsers()

pars_archipfs = subp.add_parser('archipfs', help='archives the given files for their associated versions using IPFS')
pars_archipfs.add_argument('mod', help='path to the mod\'s json file')
pars_archipfs.add_argument('files', nargs='+', help='list of files to add to the archive')
pars_archipfs.set_defaults(func=archive_ipfs)

pars_orphans = subp.add_parser('check', help='finds orphaned files and missing archived files')
pars_orphans.set_defaults(func=check)

args = parser.parse_args()
args.func(args)
