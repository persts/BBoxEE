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

        self.original_file_list = []
        self.data = data
        
        self.pb_cancel.clicked.connect(self.filtered_list.emit(self.original_file_list))
        self.pb_filter_confirmed.clicked.connect(self.filter)
 


    def filter(self):
        if len(self.image_list) > 0:
            label = self.input_label.text()

            if label == '':
                self.image_list = self.original_file_list
            else:
                self.image_list = []
                #Filter flagged images and case sensitive
                if self.cb_flagged.isChecked() and self.cb_case_sensitive.isChecked():
                    for image in self.data['review']:
                        ann = self.data['review'][image]['annotations']
                        for a in ann:
                            if a['label'].startswith(label):
                                self.image_list.append(image)
                                break
                #Filter flagged images and case insensitive
                elif self.cb_flagged.isChecked():
                    label = label.lower()
                    for image in self.data['review']:
                        ann = self.data['review'][image]['annotations']
                        for a in ann:
                            if a['label'].lower().startswith(label):
                                self.image_list.append(image)
                                break
                #Filter all images and case sensitive
                elif self.cb_case_sensitive.isChecked():
                    for image in self.data['images']:
                        ann = self.data['images'][image]['annotations']
                        for a in ann:
                            if a['label'].startswith(label):
                                self.image_list.append(image)
                                break
                #Filter all images and case insensitive
                else:
                    label = label.lower()
                    for image in self.data['images']:
                        ann = self.data['images'][image]['annotations']
                        for a in ann:
                            if a['label'].lower().startswith(label):
                                self.image_list.append(image)
                                break
                
                #add if len(image_list) == 0:   no results Qmessage and quit dialog?

                self.image_list.sort()
            self.filtered_list.emit(self.image_list)

    if __name__ == "__main__":
        app = QtWidgets.QApplication(sys.argv)
        dialog = QtWidgets.QDialog()
        dialog.show()
        sys.exit(app.exec_())


    # def load_ui(self):
    #     loader = QUiLoader()
    #     path = os.fspath(Path(__file__).resolve().parent / "form.ui")
    #     ui_file = QFile(path)
    #     ui_file.open(QFile.ReadOnly)
    #     loader.load(ui_file, self)
    #     ui_file.close()


# if __name__ == "__main__":
#     app = QApplication([])
#     widget = FilterDialog()
#     widget.show()
#     sys.exit(app.exec_())
