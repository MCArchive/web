"""
This module contains functions for managing the metadata repo with git.
"""

import git

class MetaRepo(object):
    """
    Wraps the `Repository` libgit2 object and provides useful functionality.
    """
    def __init__(self, path):
        self.repo = git.Repo(path)

    def current_rev_str(self):
        return self.repo.commit('master').hexsha

    def check_updates(self):
        """
        Returns true if the repo has updates available. This does a git fetch.
        """
        origin = self.repo.remotes.origin
        commits_behind = self.repo.iter_commits('master..origin/master')
        return sum(1 for _ in commits_behind) > 0

    def pull_updates(self):
        """
        Pulls any available updates
        """
        origin = self.repo.remotes.origin
        fr = origin.pull()
