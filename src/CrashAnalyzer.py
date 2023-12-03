#!/usr/bin/env python3

import sys
import os
import signal
import argparse
from PyQt5 import QtWidgets
from CrashAnalyzer.ui import MainWindow

def sigint_handler(sig, frame):
    logger.warning('Main thread got interrupted, shutting down...')
    os._exit(1)

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Crash Analyzer")
parser.add_argument("file", type=str, help="Directly load given file", nargs="?")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="INFO")
args = parser.parse_args()

import json, logging, logging.config
with open(os.path.join(os.path.dirname(sys.argv[0]), "conf", "logger.json"), 'r') as logging_configuration_file:
    logger_config = json.load(logging_configuration_file)
logger_config["handlers"]["stderr"]["level"] = args.log
logging.config.dictConfig(logger_config)
logger = logging.getLogger(__name__)
logger.info('Logger configured...')

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
