from ui import Main_Ui
import sys, os
from PyQt5 import QtWidgets
import argparse

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Log Viewer")
parser.add_argument("file", type=str, help="Directly load given file", nargs="?")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="DEBUG")
args = parser.parse_args()

import json, logging, logging.config
with open(os.path.join(os.path.dirname(sys.argv[0]), "conf", "logger.json"), 'r') as logging_configuration_file:
    logger_config = json.load(logging_configuration_file)
logger_config["handlers"]["stderr"]["level"] = args.log
logging.config.dictConfig(logger_config)
logger = logging.getLogger(__name__)
logger.info('Logger configured...')

# display GUI
application_run = QtWidgets.QApplication(sys.argv)
Main_application = Main_Ui()
Main_application.show()
application_run.exec_()