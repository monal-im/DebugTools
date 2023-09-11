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
            with open(self.path, 'wb') as fp:
                json.dump(defaultDictionary, fp)

    def store(self):
        with open(self.path, 'wb') as fp:
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

    def _widgetName(self, widget):
        names = []
        obj = widget
        while obj != None:
            names.append(obj.objectName())
            obj = obj.parent()
        name = ".".join(names[::-1])
        logger.error("full name: " + name)
        return name