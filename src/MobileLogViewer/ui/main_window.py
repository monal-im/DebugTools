from kivy.core.window import Window
from kivy.app import App

from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.clock import mainthread
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.factory import Factory
from kivy.utils import platform

import functools
import os
from collections import defaultdict
from jnius import autoclass, cast

# Just import if the os is Android to avoid Android peculiarities
if platform == "android":
    from android import activity, mActivity, permissions
    J_FileOutputStream = autoclass("java.io.FileOutputStream")
    J_FileUtils = autoclass("android.os.FileUtils")
    #J_Intent = autoclass("android.content.Intent")
    #J_PythonActivity = autoclass('org.kivy.android.PythonActivity')
    permissions.request_permissions([permissions.Permission.READ_EXTERNAL_STORAGE, permissions.Permission.WRITE_EXTERNAL_STORAGE])

from shared.utils.constants import LOGLEVELS
from shared.storage import Rawlog
from shared.utils import Paths
from shared.ui.mobile_about_dialog import MobileAboutDialog

import logging
logger = logging.getLogger(__name__)

class MainWindow(App):
    def build(self):
        Window.clearcolor = (239, 239, 239, 1)
        self.icon = Paths.get_art_filepath("icon.png")
        self.title = "Monal Mobile Log Viewer"

        self.rawlog = Rawlog()

        # Configure logFlags2color
        self.logFlag2color = defaultdict(lambda: (0, 0, 0), {v: {
            "ERROR":    (255, 0, 0, 0),
            "WARNING":  (254, 134, 0, 0),
            "INFO":     (0, 238, 0, 1),
            "DEBUG":    (1, 175, 255, 1),
            "VERBOSE":  (148, 149, 149, 1),
            "STDERR":   (255, 0, 0, 1),
            "STDOUT":   (0, 0, 0, 1),
            "STATUS":   (255, 255, 255, 0)
        }[k] for k, v in LOGLEVELS.items()})

        logger.debug("Creating ui elements...")
        self.layout = GridLayout(rows = 3)

        self.uiActionBar = Factory.ActionBar(pos_hint = {'top': 1})
        self.uiActionView = Factory.ActionView()
        self.uiActionGroup = Factory.ActionGroup(text = 'File', mode = 'spinner')

        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'Open File...', on_press = self.selectFile))
        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'About', on_press = MobileAboutDialog))

        self.uiActionView.add_widget(self.uiActionGroup)
        self.uiActionView.add_widget(Factory.ActionPrevious(title = '', with_previous = False, app_icon = Paths.get_art_filepath("quitIcon.png"), on_press = self.quit))
        self.uiActionBar.add_widget(self.uiActionView)

        self.uiLabel_selectedFile = Label(text = "Selected File: None", size_hint = (1, None), color = (0, 0, 0, 1))
        self.uiLabel_selectedFile.bind(
            width=lambda *x: self.uiLabel_selectedFile.setter("text_size")(self.uiLabel_selectedFile, (self.uiLabel_selectedFile.width, None)),
            texture_size=lambda *x: self.uiLabel_selectedFile.setter("height")(self.uiLabel_selectedFile, self.uiLabel_selectedFile.texture_size[1])
        )

        self.uiScrollWidget_logs = ScrollView()
        self.uiLayout_logs = GridLayout(cols = 1, spacing = 10, size_hint_y = None)
        self.uiLayout_logs.bind(minimum_height = self.uiLayout_logs.setter("height"))
        self.uiScrollWidget_logs.add_widget(self.uiLayout_logs)
        
        gridLayout_menueBar = GridLayout(cols = 1, size_hint = (1, 0.1))
        gridLayout_menueBar.add_widget(self.uiLabel_selectedFile)

        self.layout.add_widget(self.uiActionBar)
        self.layout.add_widget(gridLayout_menueBar)
        self.layout.add_widget(self.uiScrollWidget_logs)

        # Just import if the os is Android to avoid Android peculiarities
        if platform == "android":
            activity.bind(on_new_intent=self.on_new_intent)

        return self.layout
        
    def quit(self, *args):
        self.stop()

    def on_start(self, *args):
        # Just import if the os is Android to avoid Android peculiarities
        if platform == "android":
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
        # Create popup window to select file
        logger.debug("Creating popup dialog for file selection...")
        layout = GridLayout(rows = 2)

        logger.debug("Creating popup buttons...")
        inLayout = GridLayout(cols = 2, size_hint = (1, 0.1))
        closeButton = Button(text = "Cancel", size_hint = (0.5, 0.5))
        openButton = Button(text = "Open", size_hint = (0.5, 0.5))
        inLayout.add_widget(closeButton)
        inLayout.add_widget(openButton)

        layout = GridLayout(cols = 1, padding = 10) 
  
        self.uiFileChooserListView_file = FileChooserListView() 

        layout.add_widget(self.uiFileChooserListView_file) 
        layout.add_widget(inLayout)        

        popup = Popup(title = "MMLV | Choose File", content = layout)   
        popup.open()    

        closeButton.bind(on_press = popup.dismiss) 
        openButton.bind(on_press = functools.partial(self.openFile, popup)) 
  
    def openFile(self, popup, *args):
        popup.dismiss()
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
            item_with_color = Label(text = formattedEntry, size_hint = (1, None), color = self.logFlag2color[entry["flag"]])
            item_with_color.bind(
                width=lambda *x: item_with_color.setter("text_size")(item_with_color, (item_with_color.width, None)),
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