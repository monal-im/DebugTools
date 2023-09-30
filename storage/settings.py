import json, logging
from PyQt5 import QtGui, QtCore
from utils import paths

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
    
    def storePreferences(self, values):
        for color in values["color"]:
            self.data["color"][list(color.keys())[0]]["data"].clear()
            for index in range(len(color)):
                self.data["color"][list(color.keys())[0]]["data"] = list(color.values())[index]

        for name in values["history"]:
            listWidget = list(name.keys())[0]
            self.data["combobox"][listWidget] = [name[listWidget].item(index).text() for index in range(name[listWidget].count())]

        for widget in values["misc"]:
            self.data["misc"][list(widget.keys())[0]] = self.getMiscWidgetText(widget[list(widget.keys())[0]])

        self._store()

    def getMiscWidgetText(self, widget):
        if str(type(widget)) == "<class 'PyQt5.QtWidgets.QSpinBox'>":
            return widget.value()
        if str(type(widget)) == "<class 'PyQt5.QtWidgets.QLineEdit'>":
            return widget.text()
        if str(type(widget)) == "<class 'PyQt5.QtWidgets.QCheckBox'>":
            return widget.isChecked()
    
    def getComboboxHistory(self, combobox):
            name = self._widgetName(combobox)
            if name in self.data["combobox"]:
                return self.data["combobox"][name]
            return []

    def loadDimensions(self, widget):
        if self._widgetName(widget) in self.data["dimensions"]:
            widget.restoreGeometry(QtCore.QByteArray.fromBase64(bytes(self.data["dimensions"][self._widgetName(widget)], "UTF-8")))

    def storeDimension(self, widget):
        self.data["dimensions"][self._widgetName(widget)] = str(widget.saveGeometry().toBase64(), "UTF-8")
        self._store()

    def loadState(self, widget):
        if self._widgetName(widget) in self.data["dimensions"]:
            widget.restoreState(QtCore.QByteArray.fromBase64(bytes(self.data["dimensions"][self._widgetName(widget)], "UTF-8")))

    def storeState(self, widget):
        self.data["dimensions"][self._widgetName(widget)] = str(widget.saveState().toBase64(), "UTF-8")
        self._store()

    def setComboboxHistory(self, combobox, history):
        self.data["combobox"][self._widgetName(combobox)] = history
        self._store()

    def getTupleColorLen(self, name):
        return self.data["color"][name]["len"]

    def getQColor(self, name):
        return self.getQColorTuple(name)[0]
    
    def getCssColor(self, name):
        return self.getCssColorTuple(name)[0]
        
    def getColor(self, name):
        return self.getColorTuple(name)[0]

    def getQColorTuple(self, name):
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = QtGui.QColor(  *colorList[color] )
        return colorList
    
    def getCssColorTuple(self, name):
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            if colorList[color] != None:
                colorList[color] = "#{:02x}{:02x}{:02x}".format( *colorList[color] )
        return colorList
        
    def getColorTuple(self, name):
        colorList = []
        for color in self.data["color"][name]["data"]:
            colorList.append(color)
        return colorList
    
    def setQColorTuple(self, name, colors):
        for color in range(len(colors)):
            if color == None:
                colors[color] = None
            else:
                colors[color] = QtGui.QColor.red(colors[color]), QtGui.QColor.green(colors[color]), QtGui.QColor.blue(colors[color])
        self.setColorTuple(name, colors)

    def setCssTuple(self, name, colors):
        for color in range(len(colors)):
            if colors[color] == None:
                colors[color] = None
            else:
                colors[color] = list(int(colors[color].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.setColorTuple(name, colors)

    def setColorTuple(self, name, colors):
        self.data["color"][name]["data"] = []
        for color in range(self.data["color"][name]["len"]):
            try:
                self.data["color"][name]["data"].append(colors[color])
            except:
                self.data["color"][name]["data"].append(None)
        self._store()

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
