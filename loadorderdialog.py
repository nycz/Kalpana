import json, os.path

from imports import QtGui, SIGNAL, Qt

class LoadOrderDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)

        self.main = parent
        self.setWindowTitle('Plugin load order')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        layout = QtGui.QVBoxLayout()

        self.loadorder_path = os.path.join(self.main.cfgdir, 'loadorder.conf')

        with open(self.loadorder_path, encoding='utf-8') as f:
            loadorder = json.loads(f.read())

        if not loadorder:
            layout.addWidget(QtGui.QLabel("No plugins available"))
            self.pluginlist_widget = None
        else:
            self.donothing = False
            self.pluginlist_widget = QtGui.QListWidget(self)
            for pname, checked in loadorder:
                item = QtGui.QListWidgetItem(pname)
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                self.pluginlist_widget.addItem(item)
            self.pluginlist_widget.setCurrentRow(0)

            layout.addWidget(self.pluginlist_widget)

            infolabel = QtGui.QLabel(
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

            def move_item_up():
                move_item(-1)
            def move_item_down():
                move_item(1)

            QtGui.QShortcut(QtGui.QKeySequence('Left'), self, move_item_up)
            QtGui.QShortcut(QtGui.QKeySequence('Right'), self, move_item_down)
            QtGui.QShortcut(QtGui.QKeySequence('Escape'), self, self.close)

        self.setLayout(layout)

        self.show()

    def closeEvent(self, event):
        if self.pluginlist_widget:
            out = []
            for i in range(self.pluginlist_widget.count()):
                item = self.pluginlist_widget.item(i)
                out.append((item.text(), item.checkState()==Qt.Checked))
            with open(self.loadorder_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(out, ensure_ascii=False, indent=2))
        event.accept()