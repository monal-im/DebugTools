from ui import Main_Ui
import sys
from PyQt5 import QtWidgets

# display GUI
application_run = QtWidgets.QApplication(sys.argv)
Main_application = Main_Ui()
Main_application.show()
application_run.exec_()