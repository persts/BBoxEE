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
from PyQt6 import QtWidgets, QtCore

from bboxee.gui import MainWindow
from bboxee import ExceptionHandler

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    QtCore.QDir.addSearchPath('icons', './icons/')
    # handler = ExceptionHandler()
    screen = app.primaryScreen()
    for s in app.screens():
        if screen.geometry().width() < s.geometry().width():
            screen = s
    gui = MainWindow(int(screen.geometry().height() * 0.025))
    # handler.exception.connect(gui.display_exception)
    gui.show()
    gui.windowHandle().setScreen(screen)
    gui.resize(int(screen.geometry().width()), int(screen.geometry().height() * 0.85))

    sys.exit(app.exec())
