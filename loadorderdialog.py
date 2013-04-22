# Copyright nycz 2011-2013

# This file is part of Kalpana.

# Kalpana is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Kalpana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Kalpana. If not, see <http://www.gnu.org/licenses/>.


import json
import os.path

from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from libsyntyche.common import set_hotkey, read_json, write_json


class LoadOrderDialog(QtGui.QDialog):
    def __init__(self, parent, loadorder_path):
        super().__init__(parent)
        class LoadOrderLabel(QtGui.QLabel): pass
        self.loadorder_path = loadorder_path
        self.setWindowTitle('Plugin load order')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        layout = QtGui.QVBoxLayout(self)

        loadorder = read_json(self.loadorder_path)

        if not loadorder:
            layout.addWidget(LoadOrderLabel("No plugins available"))
            self.pluginlist_widget = None
        else:
            self.pluginlist_widget = QtGui.QListWidget(self)
            for pname, checked in loadorder:
                item = QtGui.QListWidgetItem(pname)
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                self.pluginlist_widget.addItem(item)
            self.pluginlist_widget.setCurrentRow(0)

            layout.addWidget(self.pluginlist_widget)

            infolabel = LoadOrderLabel(
                "Use left and right arrow to move the selected plugin up and "
                "down. Higher up means loaded earlier. Lower down means "
                "loaded later and possibly overriding earlier plugins.\n"
                "Toggle activation with space."
            )
            infolabel.setWordWrap(True)
            layout.addWidget(infolabel)

            def move_item(diff):
                """ diff is -1 for up and +1 for down """
                plw = self.pluginlist_widget
                pos = plw.currentRow()
                if pos+diff not in range(plw.count()):
                    return
                plw.insertItem(pos+diff, plw.takeItem(pos))
                plw.setCurrentRow(pos+diff)

            set_hotkey('Left', self, lambda: move_item(-1))
            set_hotkey('Right', self, lambda: move_item(1))
            set_hotkey('Escape', self, self.close)

        self.show()

    def closeEvent(self, event):
        if self.pluginlist_widget:
            out = []
            for i in range(self.pluginlist_widget.count()):
                item = self.pluginlist_widget.item(i)
                out.append((item.text(), item.checkState()==Qt.Checked))
            write_json(self.loadorder_path, out)
        event.accept()
