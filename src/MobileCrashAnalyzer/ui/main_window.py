from kivy.core.window import Window
from kivy.app import App
from kivy.factory import Factory
from kivy.clock import mainthread
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.carousel import Carousel

import os
import functools
from jnius import autoclass, cast

from shared.storage import CrashReport, Rawlog
from shared.utils import Paths
from shared.ui.mobile_about_dialog import MobileAboutDialog

# Just import if the os is Android to avoid Android peculiarities
try:
    from android import activity, mActivity, permissions
    J_FileOutputStream = autoclass("java.io.FileOutputStream")
    J_FileUtils = autoclass("android.os.FileUtils")
    J_Intent = autoclass("android.content.Intent")
    J_PythonActivity = autoclass('org.kivy.android.PythonActivity')
    J_Environment = autoclass("android.os.Environment")
    J_Settings = autoclass("android.provider.Settings")
    J_Uri = autoclass("android.net.Uri")
    OPERATING_SYSTEM = "Android"
except:
    OPERATING_SYSTEM = None

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
        self.lastCarouselIndex = -1

        logger.debug("Creating ui elements")
        self.layout = GridLayout(rows=2)

        # Create actionbar
        self.uiActionBar = Factory.ActionBar(pos_hint={'top': 1})

        self.uiCarouselWidget = Carousel(direction='right')
        # use touch_up to make sure carousel movement has finished when invoking our handler
        self.uiCarouselWidget.bind(index=self.onCarouselChanged)
        self.uiCarouselWidget.ignore_perpendicular_swipes = True

        self.layout.add_widget(self.uiActionBar)
        self.layout.add_widget(self.uiCarouselWidget)

        # Use if the os is Android to avoid Android peculiarities
        if OPERATING_SYSTEM == "Android":
            activity.bind(on_new_intent=self.on_new_intent)
            permissions.request_permissions([permissions.Permission.READ_EXTERNAL_STORAGE, permissions.Permission.WRITE_EXTERNAL_STORAGE])

        self.rebuildActionBar()
        return self.layout

    def quit(self, *args):
        self.stop()

    def onCarouselChanged(self, *args):
        if self.report == None:
            return;
        # rebuild ui if the carousel index changed
        if self.uiCarouselWidget.index != self.lastCarouselIndex:
            logger.info("Showing report having index '%d' and name '%s'..." % (self.uiCarouselWidget.index, self.report[self.uiCarouselWidget.index]["name"]))
            
            # save current carousel position used to display actionbar title
            # this will be used to check if we have to reload our actionbar
            self.lastCarouselIndex = self.uiCarouselWidget.index
            
            # Rebuild ActionBar with new parameters
            self.rebuildActionBar()

    def on_start(self, *args):
        # Use if the os is Android to avoid Android peculiarities
        if OPERATING_SYSTEM == "Android":
            logger.info("Asking for permission for external storage")
            self.permissions_external_storage()

            context = cast('android.content.Context', mActivity.getApplicationContext())
            logger.info(f"Startup application context: {context}")
            intent = mActivity.getIntent()

            logger.info(f"Got startup intent: {intent}")
            if intent:
                self.on_new_intent(intent)
    
    #see https://github.com/termux/termux-app/blob/74b23cb2096652601050d0f4951f9fb92577743c/app/src/main/java/com/termux/filepicker/TermuxFileReceiverActivity.java#L70
    @mainthread
    def on_new_intent(self, intent):
        if OPERATING_SYSTEM == "Android":
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
                self.loadFile(cacheFile)
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
                    self.loadfile(cacheFile)
                    os.remove(cacheFile)
                else:
                    logger.info("Str based uri found...")
                    cacheFile = Paths.get_cache_filepath("intent.file")
                    if os.path.exists(cacheFile):
                        os.remove(cacheFile)
                    J_FileUtils.copy(contentResolver.openInputStream(intent.getData()), J_FileOutputStream(cacheFile))
                    self.loadFile(cacheFile)
                    os.remove(cacheFile)
               
                """

    # See: https://stackoverflow.com/questions/64849485/why-is-filemanager-not-working-on-android-kivymd
    def permissions_external_storage(self, *args):                  
        if not J_Environment.isExternalStorageManager():
            try:
                logger.debug("Ask for ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION")
                context = mActivity.getApplicationContext()
                uri = J_Uri.parse("package:" + context.getPackageName())
                intent = J_Intent(J_Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, uri)
            except Exception as e:
                logger.debug("ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION Failed! Open ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION")
                intent = J_Intent(J_Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
            currentActivity = cast("android.app.Activity", J_PythonActivity.mActivity)
            currentActivity.startActivityForResult(intent, 101)

    def openFile(self, *args):
        logger.debug("Create file select popup dialog...")

        self.uiFileChooserListView_file = FileChooserListView(path=Paths.get_user_documents_dir(), filters=["*.mcrash", "*.mcrash.gz"])

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
            self.resetUi()
            self.loadFile(self.uiFileChooserListView_file.selection[0])

        openButton.bind(on_press = openClosure) 
        closeButton.bind(on_press = popup.dismiss) 
        popup.open()

    def loadFile(self, filename):
        logger.info("Loading crash report at '%s'..." % filename)
        try:
            self.report = CrashReport(filename)
            logger.info("Crash report now loaded...")

            logger.info("Creating report widgets...")
            for index in range(len(self.report)):
                # we want our keyboard to not show up on every touch and we don't want the user to be able to change the contents of the text input
                # note: if using self.uiTextInput.readonly = True, no touch events will be handled anymore not even scrolling ones
                uiTextInput = TextInput(text = "", keyboard_mode = "managed")
                uiTextInput.insert_text = lambda self, substring, from_undo=False: False
                #self.uiTextInput.bind(minimum_height=self.uiTextInput.setter("height"))

                if self.report[index]["type"] in ("*.rawlog", "*.rawlog.gz"):
                    logger.warning("Only showing last %d lines of rawlog..." % RAWLOG_TAIL)
                    text = self.report.display_format(index, tail = RAWLOG_TAIL)
                else:
                    text = self.report.display_format(index)
            
                uiTextInput.text = text

                # If the current part is not rawlog/rawlog.gz, the cursor is set to the beginning (0,0)
                if self.report[index]["type"] not in ("*.rawlog", "*.rawlog.gz"):
                    uiTextInput.cursor = (0,0)

                self.uiCarouselWidget.add_widget(uiTextInput)

            logger.debug("Loading completed...")
        except Exception as ex:
            logger.warn("Exception loading crash report: %s" % str(ex))
            self.createPopup("Exception loading crash report: %s" % str(ex))
            self.resetUi()
            return
    
    def switch_part(self, index, *args):
        self.uiCarouselWidget.index = index
    
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
            for index in range(len(self.report)):
                button = Factory.ActionButton(text = self.report[index]["name"], on_press = functools.partial(self.switch_part, index))
                self.uiActionGroup.add_widget(button)
                button.texture_update()
                self.uiActionGroup.dropdown_width = max(self.uiActionGroup.dropdown_width, button.texture_size[0]) + 16

        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'Open File...', on_press = self.openFile))
        self.uiActionGroup.add_widget(Factory.ActionButton(text = 'About', on_press = MobileAboutDialog))

        self.uiActionView.add_widget(self.uiActionGroup)
        self.uiActionView.add_widget(Factory.ActionPrevious(title = self.report[self.uiCarouselWidget.index]["name"] if self.report != None else "", with_previous=False, app_icon=Paths.get_art_filepath("quitIcon.png"), on_press = self.quit))
        self.uiActionBar.add_widget(self.uiActionView)
        
        logger.info("ActionBar now repopulated...")

    def resetUi(self):
        logger.debug("Reseting ui...")
        self.uiCarouselWidget.clear_widgets()
        self.report = None
        self.lastCarouselIndex = -1
        self.rebuildActionBar()

    def createPopup(self, message):
        logger.debug("Creating Popup...")
        closeButton = Button(text = "Close", size_hint = (1, None))

        label = Label(text = "[color=ffffff] %s [/color]" % message, size_hint = (1, None), markup=True)
        label.bind(
            width=lambda *x: label.setter("text_size")(label, (label.width, None)),
            texture_size=lambda *x: label.setter("height")(label, label.texture_size[1])
        )

        uiGridLayout_popup = GridLayout(cols = 1, padding = 6) 
        uiGridLayout_popup.add_widget(label) 
        uiGridLayout_popup.add_widget(closeButton)        

        popup = Popup(title ="MMCA | Warning", content = uiGridLayout_popup)

        closeButton.bind(on_press = popup.dismiss) 
        popup.open()
