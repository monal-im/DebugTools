#!/usr/bin/env python3
import sys, os
import argparse
from PyQt5 import QtWidgets

from utils import paths
from ui import MainWindow

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Log Viewer")
parser.add_argument("file", type=str, help="Directly load given file", nargs="?")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="DEBUG")
args = parser.parse_args()

os.makedirs(paths.user_data_dir(), exist_ok=True)
os.makedirs(paths.user_log_dir(), exist_ok=True)

import json, logging, logging.config
try:
    with open(paths.get_conf_filepath("logger.json"), 'r') as logging_configuration_file:
        logger_config = json.load(logging_configuration_file)
except:
    with open(paths.get_default_conf_filepath("logger.json"), 'rb') as fp:
        logger_config = json.load(fp)
    with open(paths.get_conf_filepath("logger.json"), 'w+') as fp:
        json.dump(logger_config, fp)
logger_config["handlers"]["stderr"]["level"] = args.log
logging.config.dictConfig(logger_config)
logger = logging.getLogger(__name__)
logger.info('Logger configured...')

# display GUI
application = QtWidgets.QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
if args.file != None:
    main_window.openLogFile(args.file)
application.exec_()