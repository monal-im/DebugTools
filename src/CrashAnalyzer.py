#!/usr/bin/env python3

import sys
import os
import signal
import argparse
import lzma
import shutil
import pathlib
from PyQt5 import QtWidgets
from CrashAnalyzer.ui import MainWindow
from shared.utils import Paths

def sigint_handler(sig, frame):
    logger.warning('Main thread got interrupted, shutting down...')
    os._exit(1)

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Crash Analyzer")
parser.add_argument("file", type=str, help="Directly load given file", nargs="?")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="INFO")
args = parser.parse_args()

Paths.set_personality(__file__)
os.makedirs(Paths.user_data_dir(), exist_ok=True)
os.makedirs(Paths.user_log_dir(), exist_ok=True)

import json, logging, logging.config
try:
    with open(Paths.get_conf_filepath("logger.json"), "r") as logging_configuration_file:
        logger_config = json.load(logging_configuration_file)
except:
    print(Paths.get_default_conf_filepath("logger.json"))
    with open(Paths.get_default_conf_filepath("logger.json"), 'rb') as fp:
        logger_config = json.load(fp)
    with open(Paths.get_conf_filepath("logger.json"), 'w+') as fp:
        json.dump(logger_config, fp)
logger_config["handlers"]["stderr"]["level"] = args.log
logging.config.dictConfig(logger_config)
logger = logging.getLogger(__name__)
logger.info("Logger configured (%s)..." % Paths.get_conf_filepath("logger.json"))

# unzip compressed symbols db if present and delete the compressed version afterwards
symbols_db = pathlib.Path(Paths.get_data_filepath("symbols.db"))
symbols_db_compressed = pathlib.Path(Paths.get_default_data_filepath("symbols.db.xz"))
try:
    if symbols_db_compressed.is_file() and not symbols_db.is_file():
        logger.info("Initializing symbols.db from symbols.db.xz...")
        with lzma.open(symbols_db_compressed, 'rb') as f_in:
            with open(symbols_db, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    #if symbols_db.is_file():
    #    symbols_db_compressed.unlink(missing_ok=True)
except:
    logger.exception("Failed to prepare symbols.db file, not resymbolicating!")
        
signal.signal(signal.SIGINT, sigint_handler)
try:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if args.file != None:
        window.load_file(args.file)
    app.exec_()
except:
    logger.exception("Catched top level exception!")
