from kivy.core.window import Window
from kivy.app import App
from kivy.factory import Factory
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

import functools

from shared.storage import CrashReport
from shared.utils import Paths

import logging
logger = logging.getLogger(__name__)

class MainWindow(App):
    def build(self):
        Window.clearcolor = (239, 239, 239, 1)
        self.icon = Paths.get_art_filepath("icon.png")
        self.title = "Monal Mobile Crash Analyzer"

        self.report = None

        logger.debug("Create ui elements")
        self.layout = GridLayout(rows=2)

        # Create actionbar
        self.uiActionBar = Factory.ActionBar(pos_hint={'top': 1})
        self.createActionBar()

        self.uiScrollWidget_logs = ScrollView()
        self.uiLayout_logs = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.uiLayout_logs.bind(minimum_height=self.uiLayout_logs.setter("height"))
        self.uiScrollWidget_logs.add_widget(self.uiLayout_logs)

        self.layout.add_widget(self.uiActionBar)
        self.layout.add_widget(self.uiScrollWidget_logs)

        return self.layout

    def quit(self, *args):
        self.stop()
    
    def selectFile(self, *args):
        logger.debug("Create file select popup dialog...")

        self.uiFileChooserListView_file = FileChooserListView() 

        closeButton = Button(text = "Cancel", size_hint=(0.5, 0.5))
        openButton = Button(text = "Open", size_hint=(0.5, 0.5))
        uiGridLayout_buttons = GridLayout(cols=2, size_hint=(1, 0.1))
        uiGridLayout_buttons.add_widget(closeButton)
        uiGridLayout_buttons.add_widget(openButton)

        uiGridLayout_selectFile = GridLayout(cols = 1, padding = 10) 
        uiGridLayout_selectFile.add_widget(self.uiFileChooserListView_file) 
        uiGridLayout_selectFile.add_widget(uiGridLayout_buttons)        

        popup = Popup(title ="MMCA | Choose File", content = uiGridLayout_selectFile)   
        popup.open()    

        # Hide popup and open file, if a file is selected
        def checkSelection(*args):
            if len(self.uiFileChooserListView_file.selection) != 0:
                popup.dismiss() # Can't be executed in self.openFile
                self.openFile()

        closeButton.bind(on_press = popup.dismiss) 
        openButton.bind(on_press = checkSelection) 
  
    def openFile(self, *args):
        filename = self.uiFileChooserListView_file.selection[0]
        logger.info("Loading crash report at '%s'..." % filename)
        # instantiate a new CrashReport and load our file
        try:
            self.report = CrashReport(filename)
        except Exception as ex:
            logger.warn("Exception loading crash report: %s" % str(ex))
            self.reset_ui()
            return
        self.filename = filename
        logger.info("Crash report now loaded...")

        # Rebuild ActionBar with new parameters
        logger.debug("Rebuild ActionBar...")
        self.createActionBar()

        for index in range(len(self.report)):
            self.report[index]["data"] = "".join(str(self.report[index]["data"]).split("\n")[-256:])

        logger.debug("Load report...")
        self.switch_part(self.report[0]["name"])

    def switch_part(self, reportName, *args):
        self.emptyScrollView()

        for index in range(len(self.report)):
            if self.report[index]["name"] == reportName:
                formatterLabel = Label(text=str(self.report.display_format(index)), size_hint=(1, None), color = (0,0,0,1))
                formatterLabel.bind(
                    width=lambda *x:
                    formatterLabel.setter("text_size")(formatterLabel, (formatterLabel.width, None)),
                    texture_size=lambda *x: formatterLabel.setter("height")(formatterLabel, formatterLabel.texture_size[1])
                    )
                self.uiLayout_logs.add_widget(formatterLabel)

    def createActionBar(self, *args):
        # Rebuild ActionBar because it's impossible to change it

        # Delete old ActionBar
        if len(self.uiActionBar.children) != 0:
            self.uiActionBar.remove_widget(self.uiActionBar.children[0])

        self.uiActionView = Factory.ActionView()
        self.uiActionGroup = Factory.ActionGroup(text='File', mode='spinner')
        self.uiActionGroup.add_widget(Factory.ActionButton(text='Open File...', on_press = self.selectFile))

        # If report is open objects are loaded
        if self.report != None:
            for report in self.report:
                self.uiActionGroup.add_widget(Factory.ActionButton(text=report["name"], on_press = functools.partial(self.switch_part, report["name"])))

        self.uiActionView.add_widget(self.uiActionGroup)
        self.uiActionView.add_widget(Factory.ActionPrevious(title='', with_previous=False, app_icon=Paths.get_art_filepath("quitIcon.png"), on_press = self.quit))
        self.uiActionBar.add_widget(self.uiActionView)

    def reset_ui(self):
        logger.debug("Reset report")
        self.emptyScrollView()
        self.report = None

    def emptyScrollView(self):
        logger.debug("Empty scrollview...")
        if len(self.uiLayout_logs.children) != 0:
            self.uiLayout_logs.remove_widget(self.uiLayout_logs.children[0])
        logger.debug("Empty scrollview done...")
