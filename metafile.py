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
