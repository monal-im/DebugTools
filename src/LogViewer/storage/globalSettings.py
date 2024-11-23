import json
import os

from shared.utils import Paths

import logging
logger = logging.getLogger(__name__)

class GlobalSettingsSingleton():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalSettingsSingleton, cls).__new__(cls)
            cls._instance.path = Paths.get_conf_filepath("globalSettings.json")
            cls._instance.defaultPath = Paths.get_default_conf_filepath("globalSettings.json")
            cls._instance._load()
            logger.debug("Instanciated GlobalSettingsSingleton...")
        return cls._instance

    def getActiveProfile(self):
        return self.data["profile"]

    def setActiveProfile(self, name):
        self.data["profile"] = name
        self._store()

    def getProfiles(self):
        return [item for item in os.listdir(Paths.user_data_dir()) if item[:8] == "profile." and item[-5:] == ".json"]

    def getProfileDisplayName(self, name):
        with open(Paths.get_conf_filepath(name), 'rb') as fp:
            return json.load(fp)["displayName"]

    def _load(self):
        logger.info("Loading default globalSettings from '%s'..." % self.defaultPath)
        with open(self.defaultPath, 'rb') as fp:
            defaults = json.load(fp)
        try:
            logger.info("Loading globalSettings from '%s'..." % self.path)
            with open(self.path, 'rb') as fp:
                self.data = json.load(fp)
        except:
            logger.info("File not loadable or does not exist: '%s', loading default config." % self.path)
            self.data = defaults
            with open(self.path, 'w+') as fp:
                json.dump(self.data, fp)

    def _store(self):
        with open(self.path, 'w') as fp:
            json.dump(self.data, fp)