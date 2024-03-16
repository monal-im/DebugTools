from kivy.core.window import Window
from kivy.app import App

from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from shared.utils.constants import LOGLEVELS
from shared.storage import Rawlog
from shared.utils import Paths

import logging
logger = logging.getLogger(__name__)

class MainWindow(App):
    def build(self):
        Window.clearcolor = (239, 239, 239, 1)
        self.icon = Paths.get_art_filepath("icon.png")
        self.title = "Monal Mobile Log Viewer"

        self.rawlog = Rawlog()

        # Configure loglevels
        logger.debug("Configure loglevels")
        self.logLevels = {
            "logline-error":    (255, 0, 0, 0),
            "logline-warning":  (254, 134, 0, 0),
            "logline-info":     (0, 238, 0, 1),
            "logline-debug":    (1, 175, 255, 1),
            "logline-verbose":  (148, 149, 149, 1),
            "logline-stderr":   (255, 0, 0, 1),
            "logline-stdout":   (0, 0, 0, 1),
            "logline-status":   (255, 255, 255, 0)
            }

        self.logflag2colorMapping = {v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}

        logger.debug("Create ui elements")
        self.layout = GridLayout(rows=2)
        gridLayout_menueBar = GridLayout(cols=2, size_hint=(1, 0.1))

        self.uiLabel_selectedFile = Label(text="Selected File: None", size_hint=(1, None), color =(0, 0, 0, 1))
        self.uiLabel_selectedFile.bind(
            width=lambda *x:
            self.uiLabel_selectedFile.setter("text_size")(self.uiLabel_selectedFile, (self.uiLabel_selectedFile.width, None)),
            texture_size=lambda *x: self.uiLabel_selectedFile.setter("height")(self.uiLabel_selectedFile, self.uiLabel_selectedFile.texture_size[1]))
        self.uiButton_selectFile = Button(text="Open File", size_hint=(0.2, 0.2), on_press = self.selectFile)

        self.uiScrollWidget_logs = ScrollView()
        self.uiLayout_logs = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.uiLayout_logs.bind(minimum_height=self.uiLayout_logs.setter("height"))
        self.uiScrollWidget_logs.add_widget(self.uiLayout_logs)
        
        gridLayout_menueBar.add_widget(self.uiLabel_selectedFile)
        gridLayout_menueBar.add_widget(self.uiButton_selectFile)

        self.layout.add_widget(gridLayout_menueBar)
        self.layout.add_widget(self.uiScrollWidget_logs)

        return self.layout
    
    def selectFile(self, *args):
        # Create popup window to select file
        logger.debug("Create popup dialog for file selection")
        layout = GridLayout(rows=2)

        logger.debug("Create popup buttons")
        inLayout = GridLayout(cols=2, size_hint=(1, 0.1))
        closeButton = Button(text = "Cancel", size_hint=(0.5, 0.5))
        openButton = Button(text = "Open", size_hint=(0.5, 0.5))
        inLayout.add_widget(closeButton)
        inLayout.add_widget(openButton)

        layout = GridLayout(cols = 1, padding = 10) 
  
        self.uiFileChooserListView_file = FileChooserListView() 

        layout.add_widget(self.uiFileChooserListView_file) 
        layout.add_widget(inLayout)        

        popup = Popup(title ="MMLV | Choose File", content = layout)   
        popup.open()    

        # Hide popup and open file, if a file is selected
        def checkSelection(*args):
            if len(self.uiFileChooserListView_file.selection) != 0:
                popup.dismiss()
                self.openFile()

        closeButton.bind(on_press = popup.dismiss) 
        openButton.bind(on_press = checkSelection) 
  
    def openFile(self, *args):
        file = self.uiFileChooserListView_file.selection[0]

        # Reset ui to a sane state
        self.resetRawlog()

        self.uiLabel_selectedFile.text = "Selected File: %s " % str(file)

        logger.debug("Creating ui Items")
        def loader(entry):
            formattedEntry = "%s %s" % (entry["timestamp"], entry["message"])
            entry["__formattedMessage"] = formattedEntry
            
            # Return None if there is no formatter
            if formattedEntry == None:
                return None
            
            # Create log label
            item_with_color = Label(text=formattedEntry, size_hint=(1, None), color =self.logLevels[self.logflag2colorMapping[entry["flag"]]])
            item_with_color.bind(
                width=lambda *x:
                item_with_color.setter("text_size")(item_with_color, (item_with_color.width, None)),
                texture_size=lambda *x: item_with_color.setter("height")(item_with_color, item_with_color.texture_size[1])
                )

            return {"uiItem": item_with_color, "data": entry}

        if self.rawlog.load_file(file, custom_load_callback=loader) != True:
            self.resetRawlog()
            return
        
        # Add ui items to scrollWidget
        logger.debug("Add ui items to scrollWidget")
        for index in range(len(self.rawlog)):
            self.uiLayout_logs.add_widget(self.rawlog[index]["uiItem"])

    def resetRawlog(self):
        logger.debug("Reset rawlog")

        # Reset ui
        if len(self.rawlog) != 0:
            for index in range(len(self.rawlog)):
                self.uiLayout_logs.remove_widget(self.uiLayout_logs.children[index])
        self.uiLabel_selectedFile.text = "Selected File: None"

        # Reset self.rawlog
        self.rawlog = Rawlog()