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
from PyQt5 import QtWidgets

from bboxee.gui import MainWindow

if __name__ == "__main__":
    APP = QtWidgets.QApplication(sys.argv)
    screen = APP.primaryScreen()
    for s in APP.screens():
        if screen.geometry().width() < s.geometry().width():
            screen = s
    GUI = MainWindow(int(screen.geometry().height() * 0.025))
    GUI.show()
    GUI.windowHandle().setScreen(screen)
    GUI.resize(int(screen.geometry().width() * 0.9), int(screen.geometry().height() * 0.85))

    sys.exit(APP.exec_())
