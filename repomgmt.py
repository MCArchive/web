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
