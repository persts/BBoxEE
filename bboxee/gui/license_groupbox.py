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
from PyQt6 import QtCore, QtWidgets, uic

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(__file__)
GBOX, _ = uic.loadUiType(os.path.join(bundle_dir, 'license_groupbox.ui'))


class LicenseGroupBox(QtWidgets.QGroupBox, GBOX):
    """Group Box containing license and annotation functionality"""
    license_changed = QtCore.pyqtSignal(dict)
    apply_license = QtCore.pyqtSignal(dict)

    def __init__(self, config_data, icon_size=24, parent=None):
        """Class init function."""
        QtWidgets.QGroupBox.__init__(self, parent)
        self.setupUi(self)

        self.default = {'license': '', 'license_url': '', 'attribution': ''}
        self.last = {'license': '', 'license_url': '', 'attribution': ''}
        self.licenses = [
            {"name":
                "Attribution 4.0 International (CC BY 4.0)",
             "url":
                "https://creativecommons.org/licenses/by/4.0/"},
            {"name":
                "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)",
             "url":
                "https://creativecommons.org/licenses/by-nc/4.0/"}
        ]

        self.set_licenses({"default": self.default, "licenses": self.licenses})

        self.cbb_license.currentIndexChanged.connect(self.update_license)
        self.le_attribution.textEdited.connect(self.update_license)
        self.pb_apply_all.clicked.connect(self.apply_all)

    def apply_all(self):
        """Apply current license to all images with bounding boxes."""
        self.apply_license.emit(self.last)

    def display_license(self, license):
        """Display a license."""
        self.cbb_license.blockSignals(True)
        if license['license'] != '' and license['attribution'] != '':
            self.last = license
        index = self.cbb_license.findData(license['license_url'])
        if index == -1:
            self.cbb_license.addItem(license['license'],
                                     license['license_url'])
        index = self.cbb_license.findData(license['license_url'])
        self.cbb_license.setCurrentIndex(index)
        self.le_attribution.setText(license['attribution'])
        self.cbb_license.blockSignals(False)

    def request(self):
        """Get the last used license."""
        self.license_changed.emit(self.last)
        index = self.cbb_license.findData(self.last['license_url'])
        self.le_attribution.setText(self.last['attribution'])
        self.cbb_license.setCurrentIndex(index)
        self.cbb_license.blockSignals(False)

    def set_licenses(self, payload):
        """Populate base license data."""
        self.cbb_license.blockSignals(True)
        self.last = payload['default']
        self.licenses = payload['licenses']
        self.cbb_license.clear()
        self.cbb_license.addItem('', '')
        for entry in self.licenses:
            self.cbb_license.addItem(entry['name'], entry['url'])
        self.cbb_license.blockSignals(False)

    def update_license(self):
        """ (SLOT) Emit changes to license or attribution."""
        index = self.cbb_license.currentIndex()
        self.last['license'] = self.cbb_license.itemText(index)
        self.last['license_url'] = self.cbb_license.itemData(index)
        self.last['attribution'] = self.le_attribution.text()
        self.license_changed.emit(self.last)
