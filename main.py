# -*- coding: utf-8 -*-
#
# Animal Detection Network (Andenet)
# Copyright (C) 2017 Peter Ersts
# ersts@amnh.org
#
# --------------------------------------------------------------------------
#
# This file is part of Animal Detection Network (Andenet).
#
# Andenet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Andenet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Point Class Assigner.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import sys
from PyQt5 import QtWidgets

from andenet import ExtractWidget
from andenet import LabelWidget
from andenet import BrowserWidget

app = QtWidgets.QApplication(sys.argv)
gui = QtWidgets.QMainWindow()
gui.setWindowTitle('Animal Detection Network')
widget = QtWidgets.QTabWidget()
widget.addTab(LabelWidget(), "Annotation")
widget.addTab(ExtractWidget(), 'Extractor')
widget.addTab(BrowserWidget(), 'Browser')
gui.setCentralWidget(widget)
gui.setGeometry(10, 10, 1200, 700)
gui.show()
sys.exit(app.exec_())
