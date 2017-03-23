"""
This module contains functions for managing the metadata repo with git.
"""

import tempfile
import git

def clone_temp(url):
    """
    Clones the given remote to a temporary folder and returns it as a
    `MetaRepo`.
    """
    path = tempfile.mkdtemp()
    print('Downloading metarepo to ' + path + '...')
    repo = git.Repo.init(path)
    origin = repo.create_remote('origin', url)
    origin.fetch()
    origin.pull(origin.refs[0].remote_head)
    print('Done')
    return MetaRepo(path)

class MetaRepo(object):
    """
    Wraps the `Repository` libgit2 object and provides useful functionality.
    """
    def __init__(self, path):
        self.repo = git.Repo(path)
        self.path = path

    def current_rev_str(self):
        return self.repo.commit('master').hexsha

    def check_updates(self):
        """
        Returns true if the repo has updates available. This does a git fetch.
        """
        origin = self.repo.remote('origin')
        rcommit = origin.fetch('master')[0].commit
        return rcommit.hexsha != self.repo.commit().hexsha

    def pull_updates(self):
        """
        Pulls any available updates
        """
        origin = self.repo.remote('origin')
        fr = origin.pull('master')
