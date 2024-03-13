#!/usr/bin/env python3

import os
import argparse

from shared.utils import Paths

# Prevent kivy from logging as well
os.environ["KIVY_NO_CONSOLELOG"] = "1"

# parse commandline
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Monal Mobile Crash Analyzer")
parser.add_argument("--log", metavar='LOGLEVEL', help="Loglevel to log", default="DEBUG")
args = parser.parse_args()

Paths.set_personality(__file__)
os.makedirs(Paths.user_data_dir(), exist_ok=True)
os.makedirs(Paths.user_log_dir(), exist_ok=True)

# Configure logger
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

# Import kivy app here to "overwrite" the kivy logger
from kivy.app import App
from kivy.core.window import Window
from MobileCrashAnalyzer.ui import MainWindow

try:
    MainWindow().run()
except:
    logger.exception("Catched top level exception!")

