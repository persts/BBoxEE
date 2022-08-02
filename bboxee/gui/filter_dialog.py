# -*- coding: utf-8 -*-
#
# Bounding Box Editor and Exporter (BBoxEE)
# Author: Julie Young
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
from PyQt5 import QtCore, QtGui, QtWidgets, uic

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
DIALOG, _ = uic.loadUiType(os.path.join(bundle_dir, 'filter_dialog.ui'))


class FilterDialog(QtWidgets.QDialog, DIALOG):
    filtered_list = QtCore.pyqtSignal(list)

    def __init__(self, data, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.data = data
        
        self.pb_cancel.clicked.connect(self.close)
        self.pb_filter_confirmed.clicked.connect(self.filter)

    def filter(self):
        label = self.input_label.text()
        temp_image_list = []

        if self.cb_flagged.isChecked():
            temp_image_list = temp_image_list + self.data['review']
            if label == "":
                temp_image_list.sort()
                self.filtered_list.emit(temp_image_list)
                self.close

        if label == "":
            self.close
        else:
            for image in self.data['images']:
                ann = self.data['images'][image]['annotations']
                for a in ann:
                    if self.cb_case_sensitive.isChecked():
                        if label in a['label'] and image not in temp_image_list:
                            temp_image_list.append(image)
                            break
                    else:
                        label = label.lower()
                        if label in a['label'].lower() and image not in temp_image_list:
                            temp_image_list.append(image)
                            break
                
        if len(temp_image_list) == 0:
            message = ('No results')
            QtWidgets.QMessageBox.warning(self.parent(),
                                            'ERROR',
                                            message,
                                            QtWidgets.QMessageBox.Ok)
        else:
            temp_image_list.sort()
            self.filtered_list.emit(temp_image_list)
            self.close()
   