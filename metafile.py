import os
import os.path

import json
from jsonobject import *

class ModHash(JsonObject):
    type_ = StringProperty(name='type')
    digest = StringProperty()

class ModUrl(JsonObject):
    type_ = StringProperty(name='type')
    url = StringProperty(required=True)
    desc = StringProperty(default='')

class ModVersion(JsonObject):
    """
    Holds metadata about a specific version of a mod.
    """
    name = StringProperty(required=True)
    desc = StringProperty(default="")
    mcvsn = ListProperty(str, required=True)
    hash_ = ObjectProperty(ModHash, name='hash', required=True)
    urls = ListProperty(ModUrl, required=True)

    def visible_urls(self):
        """
        Returns a list of URLs for this version visible to the public. This
        hides our archived URL if an official one is present.
        """
        if any(map(lambda u: u.type_ == "page" or u.type_ == "original", self.urls)):
            return list(filter(lambda u: u.type_ != "archived", self.urls))
        else:
            return self.urls

class ModMeta(JsonObject):
    """
    Holds metadata about a specific mod.
    """
    name = StringProperty(required=True)
    authors = ListProperty(str, default=[])
    desc = StringProperty(default='')
    versions = ListProperty(ModVersion, required=True)


def load_mod_file(path):
    with open(path, 'r') as f:
        return ModMeta(json.load(f))

def load_mods(path):
    mods = {}
    for name in os.listdir(path):
        id = os.path.splitext(name)[0]
        mods[id] = load_mod_file(os.path.join(path, name))
    return mods
