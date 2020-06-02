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
import datetime
from PyQt5 import QtWidgets


class CocoDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('COCO Information')
        self.setMinimumSize(500, 0)
        self.setModal(True)
        date_created = datetime.datetime.now().strftime('%Y-%m-%d %H:%S:%I')
        self.info = {'description': '',
                     'url': '',
                     'version': '',
                     'year': '',
                     'contributor': '',
                     'date_created': date_created}
        self.desc = QtWidgets.QLineEdit()
        self.desc.textChanged.connect(self.update)
        self.url = QtWidgets.QLineEdit()
        self.url.textChanged.connect(self.update)
        self.version = QtWidgets.QLineEdit()
        self.version.textChanged.connect(self.update)
        self.year = QtWidgets.QLineEdit()
        self.year.textChanged.connect(self.update)
        self.contrib = QtWidgets.QLineEdit()
        self.contrib.textChanged.connect(self.update)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("Description", self.desc)
        layout.addRow("Url", self.url)
        layout.addRow("Version", self.version)
        layout.addRow("Year", self.year)
        layout.addRow("Contributor", self.contrib)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addRow(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def update(self, text=''):
        self.info['description'] = self.desc.text()
        self.info['url'] = self.url.text()
        self.info['version'] = self.version.text()
        self.info['year'] = self.year.text()
        self.info['contributor'] = self.contrib.text()
