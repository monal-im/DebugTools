from kivy.core.window import Window
from kivy.app import App
from kivy.factory import Factory
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

import functools

from jnius import autoclass, cast
from android import activity

from shared.storage import CrashReport, Rawlog
from shared.utils import Paths
from shared.ui.mobile_about_dialog import MobileAboutDialog

import logging
logger = logging.getLogger(__name__)

class MainWindow(App):
    def build(self):
        Window.clearcolor = (239, 239, 239, 1)
        self.icon = Paths.get_art_filepath("icon.png")
        self.title = "Monal Mobile Crash Analyzer"

        self.report = None
        self.currentPart = ""

        logger.debug("Create ui elements")
        self.layout = GridLayout(rows=2)

        # Create actionbar
        self.uiActionBar = Factory.ActionBar(pos_hint={'top': 1})
        self.rebuildActionBar()

        self.uiTextInput = TextInput(text = "")
        #self.uiTextInput.bind(minimum_height=self.uiTextInput.setter("height"))

        self.layout.add_widget(self.uiActionBar)
        self.layout.add_widget(self.uiTextInput)

        activity.bind(on_new_intent=self.on_new_intent)

        return self.layout

    def quit(self, *args):
        self.stop()
    
    def on_new_intent(self, intent):
        logger.info("Got new intent with action: %s" % str(intent.getAction()))
        logger.debug("Raw intent: %s" % str(intent))
        if intent.getAction() == "android.intent.action.VIEW":
            logger.info("Intent path: %s" % intent.getData().getPath())
        
        #tag = cast('android.nfc.Tag', intent.getParcelableExtra(NfcAdapter.EXTRA_TAG))
    
    def selectFile(self, *args):
        logger.debug("Create file select popup dialog...")

        self.uiFileChooserListView_file = FileChooserListView(path=Paths.get_user_documents_dir()) 

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

        closeButton.bind(on_press = popup.dismiss) 
        openButton.bind(on_press = functools.partial(self.openFile, popup)) 
  
    def openFile(self, popup, *args):
        popup.dismiss()
        filename = self.uiFileChooserListView_file.selection[0]
        logger.info("Loading crash report at '%s'..." % filename)
        # instantiate a new CrashReport and load our file
        try:
            self.report = CrashReport(filename)
        except Exception as ex:
            logger.warn("Exception loading crash report: %s" % str(ex))
            self.resetUi()
            return
        self.filename = filename
        logger.info("Crash report now loaded...")

        logger.debug("Load report...")
        self.switch_part(self.report[0]["name"])

    def switch_part(self, reportName, *args):
        self.clearUiTextInput()

        for index in range(len(self.report)):
            if self.report[index]["name"] == reportName:
                self.currentPart = reportName

                # Rebuild ActionBar with new parameters
                self.rebuildActionBar()

                if self.report[index]["type"] in ("*.rawlog", "*.rawlog.gz"):
                    text = self.report.display_format(index, tail=256)
                else:
                    text = self.report.display_format(index)
                
                self.uiTextInput.text = text
                self.uiTextInput.cursor = (0,0)

    def rebuildActionBar(self, *args):
        # Rebuild ActionBar because it's impossible to change it

        logger.debug("Rebuilding ActionBar...")

        # Delete old ActionBar content
        for child in self.uiActionBar.children:
            self.uiActionBar.remove_widget(child)

        self.uiActionView = Factory.ActionView()
        self.uiActionGroup = Factory.ActionGroup(text='File', mode='spinner')

        # If report is open objects are loaded
        if self.report != None:
            for report in self.report:
                button = Factory.ActionButton(text = report["name"], on_press = functools.partial(self.switch_part, report["name"]))
                self.uiActionGroup.add_widget(button)
                button.texture_update()
                self.uiActionGroup.dropdown_width = max(self.uiActionGroup.dropdown_width, button.texture_size[0]) + 16

        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'Open File...', on_press = self.selectFile))
        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'About', on_press = MobileAboutDialog))

        self.uiActionView.add_widget(self.uiActionGroup)
        self.uiActionView.add_widget(Factory.ActionPrevious(title = self.currentPart, with_previous=False, app_icon=Paths.get_art_filepath("quitIcon.png"), on_press = self.quit))
        self.uiActionBar.add_widget(self.uiActionView)

    def resetUi(self):
        logger.debug("Reseting ui...")
        self.clearUiTextInput()
        self.report = None

    def clearUiTextInput(self):
        logger.debug("Clearing uiTextInput...")
        self.uiTextInput.text = ""
