import os
import os.path
from collections import OrderedDict

import yaml
from jsonobject import *

class ModHash(JsonObject):
    type_ = StringProperty(name='type')
    digest = StringProperty()

class ModUrl(JsonObject):
    type_ = StringProperty(name='type')
    url = StringProperty(required=True)
    desc = StringProperty(default='')

class ModVsnFile(JsonObject):
    """
    Holds metadata about a file within a version.
    """
    filename = StringProperty(required=True)
    hash_ = ObjectProperty(ModHash, name='hash', required=True)
    ipfs = StringProperty(default='')
    urls = ListProperty(ModUrl)

    def archive_public(self):
        """
        Returns true if our archived version should be publicly available.
        """
        return not any(map(lambda u: u.type_ == "page", self.urls))

    def ipfs_avail(self):
        """
        Returns true if this file is archived in IPFS.
        """
        return self.archive_public()

    def ipfs_url(self):
        """
        Determines the URL of the archived file in IPFS (accessed via ipfs.io).
        """
        return 'https://ipfs.io/ipfs/' + self.ipfs

    def visible_urls(self):
        """
        Returns a list of URLs for this version visible to the public. This
        hides our archived URL if an official one is present.
        """
        lst = self.urls.copy()
        if self.ipfs != '' and self.archive_public():
            lst.append(ModUrl(type_="ipfs", url=self.ipfs_url()))
        return lst

class ModVersion(JsonObject):
    """
    Holds metadata about a specific version of a mod.
    """
    name = StringProperty(required=True)
    desc = StringProperty(default="")
    mcvsn = ListProperty(str, required=True)
    files = ListProperty(ModVsnFile, required=True)

    def get_file(self, fn):
        """
        Gets a file by name or returns `None`.
        """
        for file in self.files:
            if file.filename == fn:
                return file
        return None

class ModMeta(JsonObject):
    """
    Holds metadata about a specific mod.
    """
    name = StringProperty(required=True)
    authors = ListProperty(str, default=[])
    desc = StringProperty(default='')
    versions = ListProperty(ModVersion, required=True)

    def mc_versions(self):
        """
        Computes a list of all supported Minecraft versions
        """
        mcvsns = []
        for v in self.versions:
            for mcv in v.mcvsn:
                if mcv not in mcvsns:
                    mcvsns.append(mcv)
        return mcvsns

    def vsns_by_mcvsn(self):
        """
        Returns a dict mapping supported Minecraft versions to a list of
        versions that support that Minecraft version.
        """
        vsns = OrderedDict()
        for v in self.versions:
            vsns.setdefault(v.mcvsn[0], []).append(v)
        return vsns

    def get_vsn(self, vn):
        """
        Gets a version by name or returns `None`.
        """
        for vsn in self.versions:
            if vsn.name == vn:
                return vsn
        return None

def load_mod_file(path):
    with open(path, 'r') as f:
        return ModMeta(yaml.load(f))

def load_mods(path):
    mods = {}
    for name in os.listdir(path):
        id = os.path.splitext(name)[0]
        mods[id] = load_mod_file(os.path.join(path, name))
    return mods
