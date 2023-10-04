import json, sys, os, logging
from PyQt5 import QtGui

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
        self.path = os.path.join(os.path.dirname(sys.argv[0]), "storage/settings.json")
        self.defaultPath = os.path.join(os.path.dirname(sys.argv[0]), "conf/default.json")
        self.load()

    def load(self):
        try:
            with open(self.path, 'rb') as fp:
                self.data = json.load(fp)
        except:
            logger.info("storage/settings.json does not exist! Using default theme.")

            with open(self.defaultPath, 'rb') as  fp:
                defaultDictionary = json.load(fp)
            with open(self.path, 'w') as fp:
                json.dump(defaultDictionary, fp)
                self.date = defaultDictionary

    def store(self):
        with open(self.path, 'w') as fp:
            json.dump(self.data, fp)

    def getComboboxHistory(self, combobox):
            name = self._widgetName(combobox)
            if name in self.data["combobox"]:
                return self.data["combobox"][name]
            return []

    def getDimensions(self, widget):
        widget.setGeometry(
            x = self.data["dimensions"][self._widgetName(widget)]["width"],
            y = self.data["dimensions"][self._widgetName(widget)]["height"]
        )

    def setDimension(self, widget):
        self.data["dimensions"][self._widgetName(widget)] = {
            "height": widget.height(), 
            "width": widget.width()
        }

    def setComboboxHistory(self, combobox, history):
        self.data["combobox"][self._widgetName(combobox)] = history

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
            colors[color] = QtGui.QColor.red(colors[color]), QtGui.QColor.green(colors[color]), QtGui.QColor.blue(colors[color])
        self.setColorTuple(name, colors)

    def setCssTuple(self, name, colors):
        for color in range(len(colors)):
            colors[color] = list(int(colors[color].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.setColorTuple(name, colors)

    def setColorTuple(self, name, colors):
        self.data["color"][name]["data"] = []
        for color in range(self.data["color"][name]["len"]):
            try:
                self.data["color"][name]["data"].append(colors(color))
            except:
                self.data["color"][name]["data"].append(None)
        self.store()

    def _widgetName(self, widget):
        names = []
        obj = widget
        while obj != None:
            names.append(obj.objectName())
            obj = obj.parent()
        name = ".".join(names[::-1])
        logger.error("full name: " + name)
        return name