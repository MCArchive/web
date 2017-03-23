"""
This module contains functions for managing the metadata repo with git.
"""

from pygit2 import Repository

class MetaRepo(object):
    """
    Wraps the `Repository` libgit2 object and provides useful functionality.
    """
    def __init__(self, path):
        self.repo = Repository(path)

    def current_rev_str(self):
        return str(self.repo.revparse_single('HEAD').id)
