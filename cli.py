#!/usr/bin/env python

import os.path
from argparse import ArgumentParser
import tempfile
import json
import re
import hashlib
import boto3
import ipfsapi

import metafile

repo_path = 'repo'

def get_bucket(args):
    s3 = boto3.resource('s3')
    return s3.Bucket('files.mcarchive.net')

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

def set_publicity(obj, public):
    """
    Sets whether a given key in a bucket is public or not.
    """
    if public: obj.Acl().put(ACL='public-read')
    else: obj.Acl().put(ACL='private')

def upload_file(bkt, path, dfile):
    with open(path, 'rb') as f:
        obj = bkt.Object(dfile)
        obj.put(Body=f)

def file_s3_key(fpath, fhash):
    """
    Calculates the S3 key to archive a file under based on its name and hash.
    """
    return fhash + "/" + os.path.basename(fpath)

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

def upload(args):
    path = args.file
    print('Calculating file checksum')
    hash_ = hash_file(path)
    dfile = file_s3_key(path, hash_)
    print('Uploading ' + dfile)
    bkt = get_bucket(args)
    upload_file(bkt, path, dfile)
    print('Done')

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

def archive(args):
    bkt = get_bucket(args)
    mod = metafile.load_mod_file(args.mod)
    for path in args.files:
        vsn, modf = find_file_vsn(mod, path)
        if modf is None:
            print("No version found for file " + path)
            continue
        if modf.archived != '':
            print("{} is already in S3. Skipping".format(modf.filename))
            continue
        fhash = hash_file(path)
        # TODO: Check hash type
        if fhash != modf.hash_.digest:
            print("Hash mismatch for {}\nExpected:\t{}\nActual:\t{}".format(path, modf.hash_.digest, fhash))
            continue
        dfile = file_s3_key(path, fhash)
        print("Uploading file to "+dfile)
        upload_file(bkt, path, dfile)
        add_json_entry(args.mod, path, '"archived": "' + dfile + '"')
        if modf.archive_public():
            print("Making file public")
            set_publicity(bkt.Object(dfile), True)

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

def s3_to_ipfs(args):
    ipfs = ipfsapi.connect()
    bkt = get_bucket(args)
    mod = metafile.load_mod_file(args.mod)
    for vsn in mod.versions:
        for modf in vsn.files:
            if modf.archived == '':
                print('{} is not in S3. Skipping'.format(modf.filename))
                continue
            if modf.ipfs != '':
                print('{} is already in IPFS. Skipping'.format(modf.filename))
                continue
            _, path = tempfile.mkstemp()
            try:
                obj = bkt.Object(modf.archived)
                print('Fetching {} from S3'.format(modf.filename))
                obj.download_file(path)
                print('Adding to IPFS')
                result = ipfs.add(path)
                add_json_entry(args.mod, modf.filename, '"ipfs": "' + result['Hash'] + '"')
            finally:
                os.remove(path)

def check(args):
    bkt = get_bucket(args)
    mods = load_mods(args)

    print("Finding missing files referenced by versions (may take some time)")
    bad = False
    # Keep track of which files are referenced (for later)
    refed = set()
    for _, m in mods.items():
        for v in m.versions:
            for f in v.files:
                if f.archived != None and f.archived != '':
                    refed.add(f.archived)
                    try:
                        bkt.Object(f.archived).load()
                    except:
                        print('Missing ' + f.archived)
                        bad = True
    if not bad: print('All archived files accounted for')

    print('Finding orphaned files')
    bad = False
    for obj in bkt.objects.all():
        if obj.key not in refed:
            print('File ' + obj.key + ' is not refered to by any version')
            bad = True
    if not bad: print('No orphans found')

def set_acl(args):
    bkt = get_bucket(args)
    mods = load_mods(args)
    for _, m in mods.items():
        for v in m.versions:
            for f in v.files:
                if f.archived != '':
                    if f.archive_public():
                        print('Making ' + f.archived + ' public')
                        set_publicity(bkt.Object(f.archived), True)
                    else:
                        print('Making ' + f.archived + ' private')
                        set_publicity(bkt.Object(f.archived), False)


parser = ArgumentParser(description='A command line interface for managing the archive')
subp = parser.add_subparsers()

pars_archive = subp.add_parser('archive', help='archives the given files for their associated versions')
pars_archive.add_argument('mod', help='path to the mod\'s json file')
pars_archive.add_argument('files', nargs='+', help='list of files to add to the archive')
pars_archive.set_defaults(func=archive)

pars_archipfs = subp.add_parser('archipfs', help='archives the given files for their associated versions using IPFS')
pars_archipfs.add_argument('mod', help='path to the mod\'s json file')
pars_archipfs.add_argument('files', nargs='+', help='list of files to add to the archive')
pars_archipfs.set_defaults(func=archive_ipfs)

pars_s3ipfs = subp.add_parser('s3ipfs', help='adds files in S3 to IPFS')
pars_s3ipfs.add_argument('mod', help='path to the mod\'s json file')
pars_s3ipfs.set_defaults(func=s3_to_ipfs)

pars_orphans = subp.add_parser('check', help='finds orphaned files and missing archived files')
pars_orphans.set_defaults(func=check)

pars_acl = subp.add_parser('setacl', help='sets appropriate access control on ALL files (may take a while)')
pars_acl.set_defaults(func=set_acl)

pars_upload = subp.add_parser('upload', help='upload a file to the archive and print its filename')
pars_upload.add_argument('file')
pars_upload.set_defaults(func=upload)

args = parser.parse_args()
args.func(args)
