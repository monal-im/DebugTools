#!/usr/bin/env python3
import sys, os
import argparse
import signal
from PyQt5 import QtWidgets

import shared.ui.utils.helpers as sharedUiHelpers
from shared.utils import Paths
from LogViewer.storage import SettingsSingleton
from LogViewer.ui import MainWindow

def sigint_handler(sig, frame):
    logger.warning('Main thread got interrupted, shutting down...')
    os._exit(1)

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Log Viewer")
parser.add_argument("file", type=str, help="Directly load given file", nargs="?")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="DEBUG")
args = parser.parse_args()

Paths.set_personality(__file__)
os.makedirs(Paths.user_data_dir(), exist_ok=True)
os.makedirs(Paths.user_log_dir(), exist_ok=True)

import json, logging, logging.config
try:
    with open(Paths.get_conf_filepath("logger.json"), 'r') as logging_configuration_file:
        logger_config = json.load(logging_configuration_file)
except:
    with open(Paths.get_default_conf_filepath("logger.json"), 'rb') as fp:
        logger_config = json.load(fp)
    with open(Paths.get_conf_filepath("logger.json"), 'w+') as fp:
        json.dump(logger_config, fp)
logger_config["handlers"]["stderr"]["level"] = args.log
logging.config.dictConfig(logger_config)
logger = logging.getLogger(__name__)
logger.info('Logger configured...')

# display GUI
signal.signal(signal.SIGINT, sigint_handler)
try:
    application = QtWidgets.QApplication(sys.argv)
    sharedUiHelpers.applyStyle(SettingsSingleton()["uiStyle"])
    main_window = MainWindow()
    main_window.show()
    if args.file != None:
        SettingsSingleton()["lastPath"] = os.path.dirname(os.path.abspath(args.file))
        main_window.openLogFile(args.file)
    application.exec_()
except:
    logger.exception("Catched top level exception!")
