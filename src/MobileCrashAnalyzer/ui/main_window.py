from kivy.core.window import Window
from kivy.app import App
from kivy.factory import Factory
from kivy.clock import mainthread
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

import os
import functools

from jnius import autoclass, cast
from android import activity, mActivity, permissions
J_FileOutputStream = autoclass("java.io.FileOutputStream")
J_FileUtils = autoclass("android.os.FileUtils")
#J_Intent = autoclass("android.content.Intent")
#J_PythonActivity = autoclass('org.kivy.android.PythonActivity')
permissions.request_permissions([permissions.Permission.READ_EXTERNAL_STORAGE, permissions.Permission.WRITE_EXTERNAL_STORAGE])

from shared.storage import CrashReport, Rawlog
from shared.utils import Paths
from shared.ui.mobile_about_dialog import MobileAboutDialog

RAWLOG_TAIL = 256

import logging
logger = logging.getLogger(__name__)

class MainWindow(App):
    def build(self):
        logger.info("Building gui...")
        
        Window.clearcolor = (239, 239, 239, 1)
        self.icon = Paths.get_art_filepath("icon.png")
        self.title = "Monal Mobile Crash Analyzer"

        self.report = None
        self.currentPart = ""

        logger.debug("Creating ui elements")
        self.layout = GridLayout(rows=2)

        # Create actionbar
        self.uiActionBar = Factory.ActionBar(pos_hint={'top': 1})
        self.rebuildActionBar()

        # we want our keyboard to not show up on every touch and we don't want the user to be able to change the contents of the text input
        # note: if using self.uiTextInput.readonly = True, no touch events will be handled anymore not even scrolling ones
        self.uiTextInput = TextInput(text = "", keyboard_mode = "managed")
        self.uiTextInput.insert_text = lambda self, substring, from_undo=False: False
        #self.uiTextInput.bind(minimum_height=self.uiTextInput.setter("height"))

        self.layout.add_widget(self.uiActionBar)
        self.layout.add_widget(self.uiTextInput)

        activity.bind(on_new_intent=self.on_new_intent)

        return self.layout

    def quit(self, *args):
        self.stop()
    
    def on_start(self, *args):
        context = cast('android.content.Context', mActivity.getApplicationContext())
        logger.info(f"Startup application context: {context}")
        intent = mActivity.getIntent()
        logger.info(f"Got startup intent: {intent}")
        if intent:
            self.on_new_intent(intent)
    
    #see https://github.com/termux/termux-app/blob/74b23cb2096652601050d0f4951f9fb92577743c/app/src/main/java/com/termux/filepicker/TermuxFileReceiverActivity.java#L70
    @mainthread
    def on_new_intent(self, intent):
        logger.info("Got new intent with action: %s" % str(intent.getAction()))
        logger.debug("Raw intent: %s" % str(intent))
        if intent.getAction() == "android.intent.action.VIEW":
            logger.info("Intent scheme: %s" % intent.getScheme())
            logger.info("Intent type: %s" % intent.getType())
            logger.info("Intent data: %s" % intent.getData())
            logger.info("Intent path: %s" % intent.getData().getPath())
            
            uri = intent.getData()
            context = mActivity.getApplicationContext()
            contentResolver = context.getContentResolver()
            
            cacheFile = Paths.get_cache_filepath("intent.file")
            if os.path.exists(cacheFile):
                os.remove(cacheFile)
            logger.debug(f"Writing file at '{uri.getPath()}' to '{cacheFile}'...")
            bytecount = J_FileUtils.copy(contentResolver.openInputStream(uri), J_FileOutputStream(cacheFile))
            logger.debug(f"{bytecount} bytes copied...")
            self.openFile(cacheFile)
            os.remove(cacheFile)
            
            """
            logger.info("Intent uri: %s" % intent.getParcelableExtra(J_Intent.EXTRA_STREAM))
            logger.info("Intent text: %s" % intent.getStringExtra(J_Intent.EXTRA_TEXT))
            uri = intent.getParcelableExtra(J_Intent.EXTRA_STREAM)
            context = mActivity.getApplicationContext()
            contentResolver = context.getContentResolver()
            if uri != None and type(uri) != str:
                logger.info("Real android.net.Uri found...")
                uri = cast("android.net.Uri", uri)
                if uri.getScheme().lower() != 'content':
                    logger.error("Uri scheme not supported: '%s'" % uri.getScheme())
                    return
                cacheFile = Paths.get_cache_filepath("intent.file")
                if os.path.exists(cacheFile):
                    os.remove(cacheFile)
                J_FileUtils.copy(contentResolver.openInputStream(uri), J_FileOutputStream(cacheFile))
                self.openFile(cacheFile)
                os.remove(cacheFile)
            else:
                logger.info("Str based uri found...")
                cacheFile = Paths.get_cache_filepath("intent.file")
                if os.path.exists(cacheFile):
                    os.remove(cacheFile)
                J_FileUtils.copy(contentResolver.openInputStream(intent.getData()), J_FileOutputStream(cacheFile))
                self.openFile(cacheFile)
                os.remove(cacheFile)
            """
    
    def selectFile(self, *args):
        logger.debug("Create file select popup dialog...")

        self.uiFileChooserListView_file = FileChooserListView(path=Paths.get_user_documents_dir()) #, filters=["*.mcrash", "*.mcrash.gz"]

        closeButton = Button(text = "Cancel", size_hint=(0.5, 0.5))
        openButton = Button(text = "Open", size_hint=(0.5, 0.5))
        uiGridLayout_buttons = GridLayout(cols=2, size_hint=(1, 0.1))
        uiGridLayout_buttons.add_widget(closeButton)
        uiGridLayout_buttons.add_widget(openButton)

        uiGridLayout_selectFile = GridLayout(cols = 1, padding = 10) 
        uiGridLayout_selectFile.add_widget(self.uiFileChooserListView_file) 
        uiGridLayout_selectFile.add_widget(uiGridLayout_buttons)        

        popup = Popup(title ="MMCA | Choose File", content = uiGridLayout_selectFile)   
        def openClosure(*args):
            popup.dismiss()
            self.openFile(self.uiFileChooserListView_file.selection[0])
        openButton.bind(on_press = openClosure) 
        closeButton.bind(on_press = popup.dismiss) 
        popup.open()
  
    def openFile(self, filename):
        logger.info("Loading crash report at '%s'..." % filename)
        try:
            self.report = CrashReport(filename)
        except Exception as ex:
            logger.warn("Exception loading crash report: %s" % str(ex))
            self.resetUi()
            #TODO: show warning dialog with exception info
            return
        logger.info("Crash report now loaded...")

        logger.debug("Showing first report part...")
        self.switch_part(self.report[0]["name"])

    def switch_part(self, reportName, *args):
        self.clearUiTextInput()

        logger.info("Showing report part '%s'..." % reportName)
        for index in range(len(self.report)):
            if self.report[index]["name"] == reportName:
                self.currentPart = reportName

                # Rebuild ActionBar with new parameters
                self.rebuildActionBar()

                if self.report[index]["type"] in ("*.rawlog", "*.rawlog.gz"):
                    logger.warning("Only showing last %d lines of rawlog..." % RAWLOG_TAIL)
                    text = self.report.display_format(index, tail = RAWLOG_TAIL)
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
