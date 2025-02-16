import json
from PyQt5 import QtGui, QtCore
import enum

from shared.utils import Paths
from .globalSettings import GlobalSettingsSingleton

import logging
logger = logging.getLogger(__name__)

class ColorType(enum.Enum):
    GLOBAL = enum.auto()
    LOGLEVEL = enum.auto()

class SettingsSingleton():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsSingleton, cls).__new__(cls)
            cls._instance.path = Paths.get_conf_filepath(GlobalSettingsSingleton().getActiveProfile())
            cls._instance.defaultPath = Paths.get_default_conf_filepath(GlobalSettingsSingleton().getDefaultProfile())
            cls._instance._load()
            logger.debug("Instanciated SettingsSingleton...")
        return cls._instance

    def reload(cls):
        logger.debug("Reload SettingsSingleton")
        cls._instance.path = Paths.get_conf_filepath(GlobalSettingsSingleton().getActiveProfile())
        cls._instance.defaultPath = Paths.get_default_conf_filepath(GlobalSettingsSingleton().getDefaultProfile())
        cls._instance._load()
    
    def __setitem__(self, key, value):
        self.data["misc"][key] = value
        self._store()  

    def __getitem__(self, key):
        if not key in self.data["misc"]:
            return None
        return self.data["misc"][key]
    
    def __delitem__(self, key):
        if not key in self.data["misc"]:
            return
        del self.data["misc"][key]
        self._store()    # automatically save on change
    
    def __len__(self):
        return len(self.data["misc"])
    
    def keys(self):
        return self.data["misc"].keys()
    
    def values(self):
        return self.data["misc"].values()
    
    def items(self):
        return self.data["misc"].items()
    
    def getComboboxHistory(self, combobox):
        return self.getComboboxHistoryByName(self._widgetName(combobox))
    
    def getComboboxNames(self):
        return list(self.data["combobox"].keys())
    
    def getComboboxHistoryByName(self, name):
        if name in self.data["combobox"]:
            return self.data["combobox"][name]
        return []
    
    def setComboboxHistoryByName(self, name, value):
        self.data["combobox"][name] = value
        self._store()

    def setComboboxHistory(self, combobox, history):
        self.setComboboxHistoryByName(self._widgetName(combobox), history)

    def loadDimensions(self, widget):
        if self._widgetName(widget) in self.data["dimensions"]:
            widget.restoreGeometry(QtCore.QByteArray.fromBase64(bytes(self.data["dimensions"][self._widgetName(widget)], "UTF-8")))

    def storeDimension(self, widget):
        self.data["dimensions"][self._widgetName(widget)] = str(widget.saveGeometry().toBase64(), "UTF-8")
        self._store()

    def storeState(self, widget):
        self.data["state"][self._widgetName(widget)] = str(widget.saveState().toBase64(), "UTF-8")
        self._store()

    def loadState(self, widget):
        if self._widgetName(widget) in self.data["state"]:
            widget.restoreState(QtCore.QByteArray.fromBase64(bytes(self.data["state"][self._widgetName(widget)], "UTF-8")))

    def setQFont(self, font, miscKey="font"):
        self[miscKey] = font.toString()
        self._store()

    def getQFont(self, miscKey="font"):
        font = QtGui.QFont()
        font.fromString(self[miscKey])
        return font

    def getLastPath(self):
        if self["lastPath"] == None or len(self["lastPath"]) == 0:
            logger.debug("Returning default last dir: %s" % Paths.get_user_documents_dir())
            return Paths.get_user_documents_dir()
        return self["lastPath"]

    def setLastPath(self, lastPath):
        self["lastPath"] = lastPath

    def clearAllFormatters(self):
        self.data["formatter"].clear()

    def setFormatter(self, name, code):
        self.data["formatter"][name] = code
        self._store()

    def getFormatterNames(self):
        return list(self.data["formatter"].keys())
    
    def getFormatter(self, name):
        return self.data["formatter"][name]
    
    def getCurrentFormatterCode(self):
        return self.data["formatter"][self.data["misc"]["currentFormatter"]]
    
    def getTabWidth(self):
        return self.data["misc"]["tabWidth"]

    def getTupleColorLen(self, name):
        return self.data["color"][name]["len"]

    def getQColor(self, name):
        return self.getQColorTuple(name)[0]
    
    def getCssColor(self, name):
        return self.getCssColorTuple(name)[0]
    
    def getColorNames(self):
        return list(self.data["color"].keys())
        
    def getColor(self, name):
        return self.getColorTuple(name)[0]

    def getQColorTuple(self, name):
        return self.getGenericQColorTuple(name, ColorType.GLOBAL)

    def setQColorTuple(self, name, colors):
        self.setGenericQColorTuple(name, colors, ColorType.GLOBAL)

    def getCssColorTuple(self, name):
        return self.getGenericCssColorTuple(name, ColorType.GLOBAL)

    def setCssColorTuple(self, name, colors):
        self.setGenericCssColorTuple(name, colors, ColorType.GLOBAL)

    def getColorTuple(self, name):
        return self.getGenericColorTuple(name, ColorType.GLOBAL)

    def setColorTuple(self, name, colors):
        self.setGenericColorTuple(name, colors, ColorType.GLOBAL)

    def getFieldNames(self):
        return list(self.data["loglevel"].keys())

    def getLoglevels(self):
        return {k:self.getLoglevel(k) for k in self.getFieldNames()}  

    def getLoglevel(self, fieldName):
        return self.data["loglevel"][fieldName]["query"]

    def getLoglevelQColor(self, name):
        return self.getLoglevelQColorTuple(name)[0]
    
    def getLoglevelCssColor(self, name):
        return self.getLoglevelCssColorTuple(name)[0]
    
    def getLoglevelColorNames(self):
        return list(self.data["loglevel"].keys())
        
    def getLoglevelColor(self, name):
        return self.getLoglevelColorTuple(name)[0]

    def getLoglevelQColorTuple(self, name):
        return self.getGenericQColorTuple(name, colorType=ColorType.LOGLEVEL)

    def getLoglevelCssColorTuple(self, name):
        return self.getGenericCssColorTuple(name, colorType=ColorType.LOGLEVEL)

    def getLoglevelColorTuple(self, name):
        return self.getGenericColorTuple(name, colorType=ColorType.LOGLEVEL)

    def setLoglevelQColorTuple(self, name, colors):
        self.setGenericQColorTuple(name, colors, colorType=ColorType.LOGLEVEL)

    def setLoglevelCssColorTuple(self, name, colors):
        self.setGenericCssColorTuple(name, colors, colorType=ColorType.LOGLEVEL)

    def setLoglevelColorTuple(self, name, colors):
        self.setGenericColorTuple(name, colors, colorType=ColorType.LOGLEVEL)

    def getGenericColorTuple(self, name, colorType=ColorType.GLOBAL):
        colorList = []
        if colorType == ColorType.LOGLEVEL:
            for color in self.data["loglevel"][name]["data"]:
                colorList.append(color)
        if colorType == ColorType.GLOBAL:
            for color in self.data["color"][name]["data"]:
                colorList.append(color)
        return colorList

    def getGenericCssColorTuple(self, name, colorType=ColorType.GLOBAL):
        if colorType == ColorType.LOGLEVEL:
            colorList = list(self.getLoglevelColorTuple(name))
        if colorType == ColorType.GLOBAL:
            colorList = list(self.getColorTuple(name))

        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = "#{:02x}{:02x}{:02x}".format(*colorList[color])
        return colorList

    def getGenericQColorTuple(self, name, colorType=ColorType.GLOBAL):
        if colorType == ColorType.LOGLEVEL:
            colorList = list(self.getLoglevelColorTuple(name))
        if colorType == ColorType.GLOBAL:
            colorList = list(self.getColorTuple(name))

        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = QtGui.QColor(*colorList[color])
        return colorList

    def setLoglevels(self, data):
        self.data["loglevel"] = data
        self._store()

    def setGenericQColorTuple(self, name, colors, colorType=ColorType.GLOBAL):
        for color in range(len(colors)):
            if colors[color] == None:
                colors[color] = None
            else:
                colors[color] = colors[color].getRgb()[:3]
        if colorType == ColorType.GLOBAL:
            self.setColorTuple(name, colors)
        if colorType == ColorType.LOGLEVEL:
            self.setLoglevelColorTuple(name, colors)

    def setGenericCssColorTuple(self, name, colors, colorType=ColorType.GLOBAL):
        for color in range(len(colors)):
            if colors[color] == None:
                colors[color] = None
            else:
                colors[color] = [int(colors[color].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        if colorType == ColorType.GLOBAL:
            self.setColorTuple(name, colors)
        if colorType == ColorType.LOGLEVEL:
            self.setLoglevelColorTuple(name, colors)

    def setGenericColorTuple(self, name, colors, colorType=ColorType.GLOBAL):
        if colorType == ColorType.GLOBAL:
            self.data["color"][name]["data"] = []
            for color in range(self.data["color"][name]["len"]):
                if name in self.data["color"]:
                    self.data["color"][name]["data"].append(colors[color])
                else:
                    self.data["color"][name]["data"].append(None)
        if colorType == ColorType.LOGLEVEL:
            self.data["loglevel"][name]["data"] = []
            for color in range(self.data["loglevel"][name]["len"]):
                if name in self.data["loglevel"]:
                    self.data["loglevel"][name]["data"].append(colors[color])
                else:
                    self.data["loglevel"][name]["data"].append(None)
        self._store()

    def getUdpEncryptionKey(self):
        return self.data["udpCredentials"]["encryptionKeys"]

    def getUdpHost(self):
        return self.data["udpCredentials"]["hosts"]

    def getUdpPort(self):
        return self.data["udpCredentials"]["port"]

    def setUdpEncryptionKey(self, keys):
        self.data["udpCredentials"]["encryptionKeys"] = keys
        self._store()

    def setUdpHost(self, hosts):
        self.data["udpCredentials"]["hosts"] = hosts
        self._store()

    def setUdpPort(self, port):
        self.data["udpCredentials"]["port"] = port
        self._store()

    def _widgetName(self, widget):
        names = []
        obj = widget
        while obj != None:
            names.append(obj.objectName())
            obj = obj.parent()
        name = ".".join(names[::-1])
        return name
        
    def _load(self):
        logger.info("Loading default settings from '%s'..." % self.defaultPath)
        with open(self.defaultPath, 'rb') as fp:
            defaults = json.load(fp)
        try:
            logger.info("Loading settings from '%s'..." % self.path)
            with open(self.path, 'rb') as fp:
                self.data = json.load(fp)
            
            # apply new defaults not yet stored in settings json
            for section in defaults:
                if section != "loglevel":
                    for key in defaults[section]:
                        if section not in self.data:
                            logger.debug("Adding whole new settings section '%s'..." % section)
                            self.data[section] = defaults[section]
                        elif key not in self.data[section]:
                            logger.debug("Adding settings key '%s' in section '%s'..." % (key, section))
                            self.data[section][key] = defaults[section][key]
            
            # remove settings not specified in defaults
            for section in list(self.data.keys()):
                if section != "loglevel":
                    if section not in defaults:
                        logger.debug("Removing whole settings section '%s'..." % section)
                        del self.data[section]
                # we don't want to delete settings keys in other sections because only misc values have a default value
                if section == "misc":
                    for key in list(self.data[section].keys()):
                        if key not in defaults[section]:
                            logger.debug("Removing settings key '%s' in section '%s'..." % (key, section))
                            del self.data[section][key]
            
        except:
            logger.info("File not loadable or does not exist: '%s', loading default config." % self.path)
            self.data = defaults
            with open(self.path, 'w+') as fp:
                json.dump(self.data, fp)

    def _store(self):
        with open(self.path, 'w') as fp:
            json.dump(self.data, fp)
