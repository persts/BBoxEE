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
from PyQt5 import QtCore


class Timer(QtCore.QObject):
    """Timer object for auto advancing through images."""
    advance = QtCore.pyqtSignal()

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.speed = 1
        self.stop_timer = False

    def run(self):
        self.advance.emit()
        if not self.stop_timer:
            QtCore.QTimer.singleShot(int(1000 / self.speed), self.run)

    @QtCore.pyqtSlot(int)
    def set_speed(self, speed):
        self.speed = speed

    def start(self):
        self.stop_timer = False
        self.run()

    def stop(self):
        self.stop_timer = True
