import os
import os.path

import json
from jsonobject import *

# FIXME: Don't hard-code this
s3url = "http://mcarch.s3-website-us-west-2.amazonaws.com/"

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
    archived = StringProperty(default='')
    hash_ = ObjectProperty(ModHash, name='hash', required=True)
    urls = ListProperty(ModUrl)

    def archive_public(self):
        """
        Returns true if our archived version should be publicly available.
        """
        return not any(map(lambda u: u.type_ == "page", self.urls))

    def archive_url(self):
        """
        Determines the URL of the archived file from the given S3 URL and the
        version's checksum.
        """
        return s3url + self.archived

    def visible_urls(self):
        """
        Returns a list of URLs for this version visible to the public. This
        hides our archived URL if an official one is present.
        """
        if self.archived != '' and self.archive_public():
            lst = self.urls.copy()
            lst.append(ModUrl(type_="archived", url=self.archive_url()))
            return lst
        else:
            return self.urls

class ModVersion(JsonObject):
    """
    Holds metadata about a specific version of a mod.
    """
    name = StringProperty(required=True)
    desc = StringProperty(default="")
    mcvsn = ListProperty(str, required=True)
    files = ListProperty(ModVsnFile, required=True)

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


def load_mod_file(path):
    with open(path, 'r') as f:
        return ModMeta(json.load(f))

def load_mods(path):
    mods = {}
    for name in os.listdir(path):
        id = os.path.splitext(name)[0]
        mods[id] = load_mod_file(os.path.join(path, name))
    return mods
