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
import os
import sys
from PyQt6 import QtWidgets, QtCore

from bboxee.gui import MainWindow, DarkModePalette
from bboxee import ExceptionHandler

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    app.setStyle('fusion')
    if app.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark:
        app.setPalette(DarkModePalette())
        # Palette colors are not honored by Qt6.5.3
        app.setStyleSheet("QToolTip { color: #ffffff; background-color: #000000; border: 0px; padding: 2px}")

    QtCore.QDir.addSearchPath('icons', os.path.join(os.path.dirname(__file__), 'icons'))

    handler = ExceptionHandler()

    screen = app.primaryScreen()
    for s in app.screens():
        if screen.geometry().width() < s.geometry().width():
            screen = s
    gui = MainWindow(int(screen.geometry().height() * 0.020))
    handler.exception.connect(gui.display_exception)
    gui.show()
    gui.windowHandle().setScreen(screen)
    gui.resize(int(screen.geometry().width() * 0.95), int(screen.geometry().height() * 0.85))

    sys.exit(app.exec())
