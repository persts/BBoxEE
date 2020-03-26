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
    screen = APP.desktop().availableGeometry()
    icon_size = int(screen.height() * 0.03)
    GUI = MainWindow(icon_size)

    GUI.resize(int(screen.width() * 0.8), screen.height() * 0.8)
    #GUI.move(int(screen.width() * -.05), 0)
    GUI.show()

    sys.exit(APP.exec_())
