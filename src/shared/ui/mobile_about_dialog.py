from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout

from jnius import autoclass, cast
from android import activity, mActivity
J_Intent = autoclass("android.content.Intent")
J_Uri = autoclass("android.net.Uri")

from shared.utils import Paths
from shared.utils.version import VERSION

import logging
logger = logging.getLogger(__name__)

def createResponsiveLabel(text):
    label = Label(text=str(text), markup=True, size_hint=(1, None))
    label.bind(
        width=lambda *x:
        label.setter("text_size")(label, (label.width, None)),
        texture_size = lambda *x: label.setter("height")(label, label.texture_size[1])
    )
    def ref_pressed(instance, value):
        logger.info(f"Reference pressed on {instance}: {value}")
        browserIntent = J_Intent(J_Intent.ACTION_VIEW, J_Uri.parse(value));
        mActivity.startActivity(browserIntent);
    label.bind(on_ref_press = ref_pressed)
    return label

def MobileAboutDialog(*args):
    logger.debug("Showing about popup dialog...")

    uiButton_close = Button(text = "Close")
    uiGridLayout_buttons = GridLayout(cols=1, size_hint=(1, None))
    uiGridLayout_buttons.add_widget(uiButton_close)

    uiGridLayout_about = GridLayout(cols=1)
    uiGridLayout_about.add_widget(createResponsiveLabel("Copyright 2024 monal-im"))
    uiGridLayout_about.add_widget(createResponsiveLabel("Project Homepage: [ref=https://github.com/monal-im/DebugTools][color=3391ff]https://github.com/monal-im/DebugTools[/color][/ref]"))
    uiGridLayout_about.add_widget(createResponsiveLabel("Umbrella Project Homepage: [ref=https://github.com/monal-im/Monal][color=3391ff]https://github.com/monal-im/Monal[/color][/ref]"))
    uiGridLayout_about.add_widget(createResponsiveLabel(" "))
    uiGridLayout_about.add_widget(createResponsiveLabel("App Icon by Ann-Sophie Zwahlen: [ref=https://art.of-sophy.ch/][color=3391ff]https://art.of-sophy.ch/[/color][/ref]"))
    uiGridLayout_about.add_widget(createResponsiveLabel(" "))
    uiGridLayout_about.add_widget(createResponsiveLabel(f"Version: {VERSION}"))
    uiGridLayout_about.add_widget(createResponsiveLabel(f"Config dir: {Paths.user_data_dir()}"))
    uiGridLayout_about.add_widget(createResponsiveLabel(" "))
    uiGridLayout_about.add_widget(uiGridLayout_buttons)

    popup = Popup(title="About", content = uiGridLayout_about)
    uiButton_close.bind(on_press = popup.dismiss)
    popup.open()
