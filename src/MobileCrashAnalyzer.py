#!/usr/bin/env python3
import os

from shared.utils import Paths

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

