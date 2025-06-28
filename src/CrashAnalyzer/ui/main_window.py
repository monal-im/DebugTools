import os
import functools
import lzma
import shutil
from PyQt5 import QtWidgets

from shared.utils import Paths, catch_exceptions, is_lzma_file
from shared.ui.utils import UiAutoloader
import shared.ui.utils.helpers as sharedUiHelpers
from shared.storage import CrashReport

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # initialize ui parts and instance vars
        self.reset_ui()
        
        # connect ui element signals
        self.uiAction_openCrashreport.triggered.connect(self.open_crashreport)
        self.uiAction_exportPartAs.triggered.connect(self.export_part)
        self.uiAction_exportAllParts.triggered.connect(self.export_all_parts)
        self.uiAction_symbolsdb.triggered.connect(self.open_symbolsdb)
        self.uiList_parts.itemDoubleClicked.connect(self.export_part)
        self.uiList_parts.currentItemChanged.connect(self.switch_part)
        self.uiAction_close.triggered.connect(self.close)
        self.uiAction_about.triggered.connect(sharedUiHelpers.action_about)
    
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
            self.uiTextEdit_data.setPlainText(self.report.display_format(self.current_index))
        self.update_statusbar()
    
    @catch_exceptions(logger=logger)
    def open_crashreport(self, _):
        # Open file Browser
        filename, check = QtWidgets.QFileDialog.getOpenFileName(self, "MCA | Choose a crashreport", "", "Monal Crashreport (*.mcrash.gz *.mcrash)(*.mcrash.gz *.mcrash);;All files (*)(*)")
        if check:
            self.load_file(filename)
    
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
            self.uiStatusbar_statusbar.showMessage("Exporting '%s' to '%s'..." % (self.report[self.current_index]["name"], filename))
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
            self.uiStatusbar_statusbar.showMessage("Exporting all parts to '%s'..." % dirname)
            try:
                self.report.export_all(dirname)
            except Exception as ex:
                logger.warn("Exception exporting part: %s" % str(ex))
                QtWidgets.QMessageBox.critical(self, "Error exporting part", "%s: %s" % (str(type(ex).__name__), str(ex)))
            self.update_statusbar()     # restore normal statusbar
    
    @catch_exceptions(logger=logger)
    def open_symbolsdb(self, _):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Open symbols.db", "", "Symbols database (*.db.xz *.db)(*.db.xz *.db);;All files (*)")
        if check:
            file = os.path.abspath(file)
            fp = open(file, 'rb')
            try:
                symbols_db_path = Paths.get_data_filepath("symbols.db")
                logger.info(f"Copying '{file}' to '{symbols_db_path}'...")
                with lzma.LZMAFile(filename=fp, mode="rb") if is_lzma_file(fp) else fp as f_in:
                    with open(symbols_db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                logger.info("Done, symbols.db is now ready to use when opening the next crash report")
            except ex:
                logger.warn("Failed to prepare symbols.db file, not resymbolicating: %s" % str(ex))
                QtWidgets.QMessageBox.critical(self, "Error importing symbols.db", "%s: %s" % (str(type(ex).__name__), str(ex)))
            finally:
                fp.close()
    
    @catch_exceptions(logger=logger)
    def load_file(self, filename):
        self.reset_ui()
            
        logger.info("Loading crash report at '%s'..." % filename)
        # instantiate a new CrashReport and load our file
        self.uiStatusbar_statusbar.showMessage("Loading crash report from '%s'..." % filename)
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
        if not self.report.resymbolicated:
            QtWidgets.QMessageBox.warning(self, "Could not resymbolicate crash report", "Either the symbols.db file is missing, or we don't have symbols for this iOS version (see 'system/os_version' in json).")
    
    @catch_exceptions(logger=logger)
    def reset_ui(self):
        self.report = None
        self.filename = None
        self.current_index = -1
        self.uiList_parts.clear()
        self.uiTextEdit_data.clear()
        self.update_statusbar()
    
    @catch_exceptions(logger=logger)
    def update_statusbar(self):
        if self.filename == None or self.report == None:
            self.uiStatusbar_statusbar.showMessage("No crash report loaded")
        elif self.current_index == -1:
            self.uiStatusbar_statusbar.showMessage(self.filename)
        else:
            self.uiStatusbar_statusbar.showMessage("%s from %s" % (self.report[self.current_index]["name"], self.filename))
        self.uiAction_exportPartAs.setEnabled(self.filename != None)
        self.uiAction_exportAllParts.setEnabled(self.filename != None)
        QtWidgets.QApplication.processEvents()          # force ui redraw and events processing
