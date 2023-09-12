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
            
            self.load() #to create self.data!?!?!

    def store(self):
        with open(self.path, 'w') as fp:
            json.dump(self.data, fp)

    def getComboboxHistory(self, combobox):
            combobox.addItems(self.data["combobox"][combobox])

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

    def setComboboxHistory(self, combobox):
        self.data["combobox"][self._widgetName(combobox)] = [combobox.itemText(i) for i in range(combobox.count())]

    def getQColorTuple(self, name):
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            colorList[color] = QtGui.QColor(  *colorList[color] )
        return colorList
    
    def getCssTuple(self, name):
        colorList = list(self.getColorTuple(name))
        for color in range(len(colorList)):
            colorList[color] = "#{:02x}{:02x}{:02x}".format( *colorList[color] )
        return colorList
        
    def getColorTuple(self, name):
        colorList = []
        for color in self.data["color"][name]:
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
        self.data["color"][name] = []
        for color in colors:
            self.data["color"][name].append(color)
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