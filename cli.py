import os.path
from argparse import ArgumentParser
import json
import re
import hashlib
import boto3

import metafile

repo_path = 'repo'

def get_bucket(args):
    s3 = boto3.resource('s3')
    return s3.Bucket('mcarch')

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

def add_archived_entry(mod, vsn, dfile):
    """
    Adds an `archived` fild to the given version in the mod file without
    disturbing the file's formatting or field ordering in the file.

    This is done by just inserting a line after the `name` field.
    """
    with open(mod, 'r') as f:
        lines = f.readlines()
    name_re = re.compile(r'( *)"name" *: *"'+vsn+r'"(,?)')
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
        print('Couldn\'t find name entry for '+vsn)
        return
    lines.insert(idx+1, indent_sp + '"archived": "' + dfile + '"' + comma + '\n')
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

def archive(args):
    bkt = get_bucket(args)
    mod = metafile.load_mod_file(args.mod)
    for path in args.files:
        vsn = next((v for v in mod.versions if v.filename == os.path.basename(path)), None)
        if vsn is None:
            print("No version found for file " + path)
            continue
        fhash = hash_file(path)
        # TODO: Check hash type
        if fhash != vsn.hash_.digest:
            print("Hash mismatch for {}\nExpected:\t{}\nActual:\t{}".format(path, vsn.hash_.digest, fhash))
            continue
        dfile = file_s3_key(path, fhash)
        print("Uploading file to "+dfile)
        upload_file(bkt, path, dfile)
        add_archived_entry(args.mod, vsn.name, dfile)
        if vsn.archive_public():
            print("Making file public")
            set_publicity(bkt.Object(dfile), True)
    #print(json.dumps(mod.to_json(), indent=4))

def check(args):
    bkt = get_bucket(args)
    mods = load_mods(args)

    print("Finding missing files referenced by versions (may take some time)")
    bad = False
    # Keep track of which files are referenced (for later)
    refed = set()
    for _, m in mods.items():
        for v in m.versions:
            if v.archived != None:
                refed.add(v.archived)
                try:
                    bkt.Object(v.archived).load()
                except:
                    print('Missing ' + v.archived)
                    bad = True
    if not bad: print('All archived files accounted for')

    print('Finding orphaned files')
    bad = False
    for obj in bkt.objects.all():
        if obj.key not in refed:
            print('File ' + obj.key + ' is not refered to by any version')
            bad = True
    if not bad: print('No orphans found')


parser = ArgumentParser(description='A command line interface for managing the archive')
subp = parser.add_subparsers()

pars_archive = subp.add_parser('archive', help='archives the given files for their associated versions')
pars_archive.add_argument('mod', help='path to the mod\'s json file')
pars_archive.add_argument('files', nargs='+', help='list of files to add to the archive')
pars_archive.set_defaults(func=archive)

pars_orphans = subp.add_parser('check', help='finds orphaned files and missing archived files')
pars_orphans.set_defaults(func=check)

pars_upload = subp.add_parser('upload', help='upload a file to the archive and print its filename')
pars_upload.add_argument('file')
pars_upload.set_defaults(func=upload)

args = parser.parse_args()
args.func(args)
