from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout

from shared.utils import Paths

from shared.utils.version import VERSION

import logging
logger = logging.getLogger(__name__)

def createResponsiveLabel(text):
    label = Label(text=str(text), size_hint=(1, None))
    label.bind(
        width=lambda *x:
        label.setter("text_size")(label, (label.width, None)),
        texture_size=lambda *x: label.setter("height")(label, label.texture_size[1])
        )
    return label

def MobileAboutDialog(*args):
    logger.debug("Create about popup dialog...")

    uiButton_close = Button(text = "Close")
    uiGridLayout_buttons = GridLayout(cols=2, size_hint=(None, None))
    uiGridLayout_buttons.add_widget(uiButton_close)

    uiGridLayout_about = GridLayout(cols=1)
    uiGridLayout_about.add_widget(createResponsiveLabel("Copyright 2023 monal-im"))
    uiGridLayout_about.add_widget(createResponsiveLabel("Project Homepage: https://github.com/monal-im/DebugTools"))
    uiGridLayout_about.add_widget(createResponsiveLabel("Umbrella Project Homepage: https://github.com/monal-im/Monal"))
    uiGridLayout_about.add_widget(createResponsiveLabel("App Icon by Ann-Sophie Zwahlen: https://art.of-sophy.ch/"))
    uiGridLayout_about.add_widget(createResponsiveLabel(Paths.user_data_dir()))
    uiGridLayout_about.add_widget(createResponsiveLabel(Paths.user_log_dir()))
    uiGridLayout_about.add_widget(uiGridLayout_buttons)

    popup = Popup(title="About", content = uiGridLayout_about)   
    popup.open()    

    uiButton_close.bind(on_press = popup.dismiss) 
