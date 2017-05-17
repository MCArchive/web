from metafile import load_mods
import repomgmt

import os
import os.path
import time
from datetime import datetime
import threading
import schedule
import logging
import threading

import ipfsapi
import ipfsutil

from flask import Flask, render_template, abort, make_response, Response
app = Flask(__name__)

# The deployment script writes information about the version to a file called
# DEPLOY_VSN. If this file is not present, we just assume we're running in
# development mode.
if os.path.isfile('DEPLOY_VSN'):
    lines = []
    with open('DEPLOY_VSN', 'r') as f:
        lines = f.readlines()
    # The first line is the git hash.
    app.config['VSN_GIT'] = lines[0]
    # more to be added later?

app.config['ANALYTICS_ID'] = os.environ.get('MCA_ANALYTICS_ID')

repo_url = 'https://github.com/MCArchive/metarepo.git'

def ipfs_try_conn(*args, **kwargs):
    try:
        return ipfsapi.connect(*args, **kwargs)
    except:
        return None

app.ipfs = ipfs_try_conn()
while app.ipfs == None:
    # If the first connection fails, assume we're running in docker and wait
    # for the service to come up.
    print('Waiting on IPFS node to be available...')
    time.sleep(1)
    print('Trying to connect')
    app.ipfs = ipfs_try_conn('ipfs')

app.repo = repomgmt.clone_temp(repo_url)
app.meta_rev = app.repo.current_rev_str()

def file_pinned(hash_, info):
    """
    Callback executed when a file is pinned.
    """
    app.pins[hash_] = info

def pin_files_async():
    """
    Pins files to IPFS in another thread
    """
    def func():
        print('Pinning files')
        app.want_pins = ipfsutil.wanted_pins(app.mods)
        ipfsutil.pin_files(app.ipfs, app.mods, callback=file_pinned)
        app.pins = ipfsutil.pinned_files(app.ipfs, app.mods)
        print('Done')
    thr = threading.Thread(target=func)
    thr.start()

def load_all_mods():
    app.mods = load_mods(os.path.join(app.repo.path, 'mods'))
    print('Creating IPFS links')
    app.flinks = ipfsutil.mk_links(app.ipfs, app.mods)
    app.pins = ipfsutil.pinned_files(app.ipfs, app.mods)
    pin_files_async()
load_all_mods()

def run_schedule(interval=1):
    """
    Continuously run scheduled jobs. Taken from
    https://github.com/mrhwick/schedule/blob/8e1d5f806d34d9ecde3c068490c8d1513ed774c3/schedule/__init__.py#L63
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        def __init__(self, app):
            super().__init__()
            self.app = app

        def run(self):
            with self.app.app_context():
                while not cease_continuous_run.is_set():
                    schedule.run_pending()
                    time.sleep(interval)

    continuous_thread = ScheduleThread(app)
    continuous_thread.start()
    return cease_continuous_run

app.update_time = datetime.now()
def repo_update():
    """
    Called periodically to update the git repository.
    """
    print('Updating repo')
    logger = logging.getLogger(__name__)
    logger.info('Checking for meta repository updates')
    if app.repo.check_updates():
        logger.info('Updates found. Pulling changes')
        app.repo.pull_updates()
        logger.info('Done. Reloading mods')
        app.meta_rev = app.repo.current_rev_str()
        load_all_mods()
    else:
        logger.info('No updates found')
    app.update_time = datetime.now()

schedule.every(3).minutes.do(repo_update)
run_schedule()

# Computes the timedelta since the last repo update.
def time_since_update():
    return datetime.now() - app.update_time

def ipfs_url(fname, fhash):
    """
    Gets the URL in IPFS of the file with the given name and hash.
    """
    return "https://ipfs.io/ipfs/" + app.flinks[(fname, fhash)]

def file_is_pinned(mhash):
    return mhash in app.pins

def archive_size():
    s = 0
    for _, p in app.pins.items():
        s += p['size']
    return s

# This adds utility functions to the template engine.
@app.context_processor
def utility_funcs():
    def meta_revision():
        return app.meta_rev
    def size_fmt(sz):
        """
        Formats a file size (in bytes) in the smallest unit that can fit a whole number.
        """
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(sz) < 1000.0: return "{:3.1f}{}B".format(sz, unit)
            sz /= 1000.0
        return "{:.1f}YB".format(sz)
    def url_type_name(ty):
        if ty == 'archived': return 'Archived File'
        elif ty == 'ipfs': return 'IPFS Download'
        elif ty == 'original': return 'Official Download'
        elif ty == 'page': return 'Official Download Page'
        else: return ty
    return dict(
        url_type_name=url_type_name,
        size_fmt=size_fmt,
        archive_size=archive_size,
        meta_revision=meta_revision,
        time_since_update=time_since_update,
        ipfs_url=ipfs_url,
        is_pinned=file_is_pinned,
        len=len # This isn't available by default for some reason
    )

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mods/')
def mod_list():
    return render_template('mods.html', mods=app.mods)

@app.route('/mods/<id>')
def mod_page(id):
    if id in app.mods:
        mod = app.mods[id]
        return render_template('mod.html', mod=mod, mod_id=id)
    else: abort(404)


@app.route('/pins')
def ipfs_pins():
    return render_template('pins.html', have_pins=app.pins, want_pins=app.want_pins)

@app.route('/pins/raw')
def ipfs_pins_raw():
    return Response('\n'.join(app.want_pins), mimetype='text/plain')
