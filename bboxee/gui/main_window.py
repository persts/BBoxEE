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
from PyQt6 import QtWidgets, QtCore

from bboxee.gui import ExportWidget
from bboxee.gui import AnnotationWidget
from bboxee.gui import AccuracyWidget
from bboxee import __version__


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, icon_size, parent=None):
        super(MainWindow, self).__init__(parent)
        template = 'Bounding Box Editor and Exporter [BBoxEE v{}]'
        self.setWindowTitle(template.format(__version__))
        self.annotation_widget = AnnotationWidget(icon_size)
        self.export_widget = ExportWidget(icon_size)
        self.widget = QtWidgets.QTabWidget()
        self.widget.addTab(self.annotation_widget, 'Annotate')
        self.widget.addTab(self.export_widget, 'Export')
        self.widget.addTab(AccuracyWidget(icon_size), 'Accuracy Report')
        self.setCentralWidget(self.widget)

        self.error_widget = QtWidgets.QTextBrowser()
        self.error_widget.setWindowTitle('EXCEPTION DETECTED')
        self.error_widget.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.error_widget.resize(900, 500)

        self.export_widget.BBX_file_selected.connect(self.load_BBX)

    def closeEvent(self, event):
        if self.annotation_widget.dirty_data_check():
            event.accept()
        else:
            event.ignore()

    def display_exception(self, error):
        self.error_widget.clear()
        for line in error:
            self.error_widget.append(line)
        self.error_widget.show()

    def load_BBX(self, file_name):
        self.widget.setCurrentWidget(self.annotation_widget)
        self.annotation_widget.load_from_file(file_name)
