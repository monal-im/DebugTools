import json
from PyQt5 import QtGui, QtCore, QtWidgets

from utils import paths

import logging
logger = logging.getLogger(__name__)

class SettingsSingleton():
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsSingleton, cls).__new__(cls)
            cls._instance.__init__()
            logger.debug("Instanciated SettingsSingleton...")
        return cls._instance
    
    def __init__(self):
        self.path = paths.get_conf_filepath("settings.json")
        self.defaultPath = paths.get_default_conf_filepath("settings.json")
        self._load()

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

    def setFormatter(self, name, code):
        if code != None:
            if name != "" and code != "":
                self.data["formatter"][name] = code
        else:
            if name in self.data["formatter"]:
                del self.data["formatter"][name]
        self._store()

    def getFormatterNames(self):
        return list(self.data["formatter"].keys())
    
    def getFormatter(self, name):
        return self.data["formatter"][name]
    
    def getCurrentFormatterCode(self):
        return self.data["formatter"][self.data["misc"]["currentFormatter"]]

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
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = QtGui.QColor(*colorList[color])
        return colorList
    
    def setQColorTuple(self, name, colors):
        for color in range(len(colors)):
            if colors[color] == None:
                colors[color] = None
            else:
                colors[color] = colors[color].getRgb()[:3]
        self.setColorTuple(name, colors)

    def getCssColorTuple(self, name):
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = "#{:02x}{:02x}{:02x}".format(*colorList[color])
        return colorList

    def setCssColorTuple(self, name, colors):
        for color in range(len(colors)):
            if colors[color] == None:
                colors[color] = None
            else:
                colors[color] = [int(colors[color].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        self.setColorTuple(name, colors)

    def getColorTuple(self, name):
        colorList = []
        for color in self.data["color"][name]["data"]:
            colorList.append(color)
        return colorList

    def setColorTuple(self, name, colors):
        self.data["color"][name]["data"] = []
        for color in range(self.data["color"][name]["len"]):
            if name in self.data["color"]:
                self.data["color"][name]["data"].append(colors[color])
            else:
                self.data["color"][name]["data"].append(None)
        self._store()

    # see https://stackoverflow.com/a/3943023
    def getCssContrastColor(self, r, g, b):
        colors = []
        for c in (r, g, b):
            c = c / 255.0
            if c <= 0.04045:
                c = c/12.92
            else:
                c = ((c+0.055)/1.055) ** 2.4
            colors.append(c)
        if 0.2126 * colors[0] + 0.7152 * colors[1] + 0.0722 * colors[2] > 0.179:
            return "rgb(0, 0, 0)"
        return "rgb(255, 255, 255)"

    def _widgetName(self, widget):
        names = []
        obj = widget
        while obj != None:
            names.append(obj.objectName())
            obj = obj.parent()
        name = ".".join(names[::-1])
        logger.error("full name: " + name)
        return name
    
    def _load(self):
        try:
            with open(self.path, 'rb') as fp:
                self.data = json.load(fp)
        except:
            logger.info("settings.json does not exist! Using default theme.")

            with open(self.defaultPath, 'rb') as fp:
                self.data = json.load(fp)
            with open(self.path, 'w+') as fp:
                json.dump(self.data, fp)

    def _store(self):
        with open(self.path, 'w') as fp:
            json.dump(self.data, fp)