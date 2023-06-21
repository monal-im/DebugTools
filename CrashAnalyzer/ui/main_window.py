import sys
import os
import logging
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from storage import SettingsSingleton, CrashReport
from utils import catch_exceptions, LambdaValueContainer

logger = logging.getLogger(__name__)

#TODO: settings: QtWidgets.QColorDialog.getColor()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # load qt ui definition file from same directory and named exactly like this file, but having extension ".ui"
        uic.loadUi(os.path.join(os.path.dirname(__file__), os.path.splitext(__file__)[0]+".ui"), self)
        #self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(sys.argv[0]), "monal_log_viewer.png")))
        
        # initialize ui parts and instance vars
        self.reset_ui()
        
        # connect ui element signals
        self.uiAction_openCrashreport.triggered.connect(self.open_crashreport)
        self.uiAction_exportPartAs.triggered.connect(self.export_part)
        self.uiAction_exportAllParts.triggered.connect(self.export_all_parts)
        self.uiList_parts.itemDoubleClicked.connect(self.export_part)
        self.uiList_parts.currentItemChanged.connect(self.switch_part)
        self.uiAction_close.triggered.connect(self.close)
    
    @catch_exceptions(logger=logger)
    def close(self, _):
        logger.info("Closing application...")
        QtWidgets.QApplication.quit()
    
    @catch_exceptions(logger=logger)
    def switch_part(self, toItem, _):
        if isinstance(toItem, int):
            self.current_index = toItem
            self.uiList_parts.setCurrentRow(self.current_index)
        else:
            self.current_index = self.uiList_parts.row(toItem)
        if self.current_index >= 0 and self.report != None and len(self.report) > 0:
            if isinstance(self.report[self.current_index]["data"], str):
                self.uiTextEdit_data.setPlainText(self.report[self.current_index]["data"])
            else:
                self.uiTextEdit_data.setPlainText("This part contains raw bytes (%s) and cannot be displayed!" % self.report[self.current_index]["type"])
        self.update_statusbar()
    
    @catch_exceptions(logger=logger)
    def open_crashreport(self, _):
        # Open file Browser
        filename, check = QtWidgets.QFileDialog.getOpenFileName(self, "MCA | Choose a crashreport", "", "Monal Crashreport (*.txt.gz)(*.txt.gz);;All files (*)(*)")
        if check:
            self.reset_ui()
            
            logger.info("Loading crash report at '%s'..." % filename)
            # instanciate a new CrashReport and load our file
            try:
                self.report = CrashReport(filename)
            except Exception as ex:
                logger.warn("Exception loading crash report: %s" % str(ex))
                self.reset_ui()
                self.update_statusbar()
                QtWidgets.QMessageBox.critical(self, "Error loading crash report", "%s: %s" % (str(type(ex).__name__), str(ex)))
                return
            self.filename = filename
            logger.info("Crash report now loaded...")
            
            # populate our parts list and load the first item
            first_text_index = None
            for index in range(len(self.report)):
                self.uiList_parts.addItem(QtWidgets.QListWidgetItem(self.report[index]["name"]))
                if first_text_index == None and isinstance(self.report[index]["data"], str):
                    first_text_index = index
            if first_text_index != None:
                self.switch_part(first_text_index, None)
            
            self.update_statusbar()
    
    @catch_exceptions(logger=logger)
    def export_part(self, _):
        if self.report == None:
            QtWidgets.QMessageBox.critical(self, "Export error", "Please open a crash report first!")
            return
        if self.current_index < 0:
            QtWidgets.QMessageBox.critical(self, "Export error", "Please select the part you want to export from the list first!")
            return
        filename, check = QtWidgets.QFileDialog.getSaveFileName(self, "MCA | Choose where to save this crash part", "",
                                "%s (%s);;All files (*)(*)" % (
                                    self.report[self.current_index]["name"],
                                    self.report[self.current_index]["type"]
                                )
        )
        if check:
            try:
                self.report.export_part(self.current_index, filename)
            except Exception as ex:
                logger.warn("Exception exporting part: %s" % str(ex))
                QtWidgets.QMessageBox.critical(self, "Error exporting part", "%s: %s" % (str(type(ex).__name__), str(ex)))
            self.update_statusbar()     # restore normal statusbar
    
    @catch_exceptions(logger=logger)
    def export_all_parts(self, _):
        if self.report == None:
            QtWidgets.QMessageBox.critical(self, "Export error", "Please open a crash report first!")
            return
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "MCA | Choose directory to save report parts to")
        if dirname != None and dirname != "":
            try:
                self.report.export_all(dirname)
            except Exception as ex:
                logger.warn("Exception exporting part: %s" % str(ex))
                QtWidgets.QMessageBox.critical(self, "Error exporting part", "%s: %s" % (str(type(ex).__name__), str(ex)))
            self.update_statusbar()     # restore normal statusbar
    
    def reset_ui(self):
        self.report = None
        self.filename = None
        self.current_index = -1
        self.uiList_parts.clear()
        self.uiTextEdit_data.clear()
        self.update_statusbar()
    
    def update_statusbar(self):
        if self.filename == None or self.report == None:
            self.uiStatusbar_statusbar.showMessage("No crash report loaded")
        elif self.current_index = -1:
            self.uiStatusbar_statusbar.showMessage(self.filename)
        else:
            self.uiStatusbar_statusbar.showMessage("%s from %s" % (self.report[self.current_index]["name"], self.filename))
        self.uiAction_exportPartAs.setEnabled(self.filename != None)
        self.uiAction_exportAllParts.setEnabled(self.filename != None)
        QtWidgets.QApplication.processEvents()          # force ui redraw and events processing
