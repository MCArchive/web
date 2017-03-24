from metafile import load_mods
import repomgmt

import os
import os.path
import time
import threading
import schedule
import logging

from flask import Flask, render_template, abort
app = Flask(__name__)

app.config['ANALYTICS_ID'] = os.environ.get('MCA_ANALYTICS_ID')

repo_url = 'https://github.com/MCArchive/metarepo.git'

app.repo = repomgmt.clone_temp(repo_url)
app.meta_rev = app.repo.current_rev_str()

def load_all_mods():
    app.mods = load_mods(os.path.join(app.repo.path, 'mods'))
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

schedule.every(3).minutes.do(repo_update)
run_schedule()

# This adds utility functions to the template engine.
@app.context_processor
def utility_funcs():
    def meta_revision():
        return app.meta_rev

    def url_type_name(ty):
        if ty == 'archived': return 'Archived File'
        elif ty == 'original': return 'Official Download'
        elif ty == 'page': return 'Official Download Page'
        else: return ty
    return dict(
        url_type_name=url_type_name,
        meta_revision=meta_revision,
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
        return render_template('mod.html', mod=mod)
    else: abort(404)
