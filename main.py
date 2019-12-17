# -*- coding: utf-8 -*-
#
# Bounding Box Editor and Exporter (BBoxEE)
# Author: Peter Ersts (ersts@amnh.org)
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network's (Andenet)
# Bounding Box Editor and Exporter (BBoxEE)
#
# BBoxEE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BBoxEE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import sys
import json
from PyQt5 import QtWidgets

from bboxee.gui import ExportWidget
from bboxee.gui import AnnotationWidget

if __name__ == "__main__":
    try:
        FILE = open("config.json", 'r')
        try:
            CONFIG = json.load(FILE)
            APP = QtWidgets.QApplication(sys.argv)
            screen = APP.desktop().availableGeometry()
            GUI = QtWidgets.QMainWindow()
            GUI.setWindowTitle('Animal Detection Network')
            WIDGET = QtWidgets.QTabWidget()
            icon_size = int(screen.height() * 0.03)
            WIDGET.addTab(AnnotationWidget(CONFIG, icon_size), 'Annotate')
            WIDGET.addTab(ExportWidget(icon_size), 'Export')
            GUI.setCentralWidget(WIDGET)
            GUI.resize(int(screen.width() * .95), screen.height() * 0.95)
            GUI.move(int(screen.width() * .05) // 2, 0)
            GUI.show()

            sys.exit(APP.exec_())
        except json.decoder.JSONDecodeError as error:
            print('Error found in config file: {}'.format(error))
        FILE.close()
    except FileNotFoundError:
        print('Config file was not found.')
