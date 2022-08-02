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
from .select_model_dialog import SelectModelDialog  # noqa: F401
from .analyst_dialog import AnalystDialog  # noqa: F401
from .coco_dialog import CocoDialog  # noqa: F401

from .accuracy_widget import AccuracyWidget  # noqa: F401
from .filter_dialog import FilterDialog # noqa: F401
from .annotation_widget import AnnotationWidget  # noqa: F401
from .export_widget import ExportWidget  # noqa: F401
from .main_window import MainWindow  # noqa: F401
