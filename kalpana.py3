#!/usr/bin/env python3
# Copyright nycz, cefyr 2011-2012

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


# [Kalpana]
# Gender: Feminine
# Usage: Indian
# Other Scripts: कल्पना (Hindi)
# Means "imagining, fantasy" in Sanskrit.

# v0.2 - added line numbers, taken from
# v0.3 - did sum shit, added dragndrop, made stuff better
# v0.4 - find(/replace)
# v0.5 - moved to git, converted to py3k, refactored, GPL'd



import datetime, json, os, os.path, platform, re, sys, subprocess

from math import ceil

from terminal import Terminal
from linewidget import LineTextWidget

try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import SIGNAL, Qt
    from PySide.QtGui import QMessageBox
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import SIGNAL, Qt
    from PyQt4.QtGui import QMessageBox


class MainWindow(QtGui.QFrame):

    def __init__(self, file_=''):
        super(MainWindow, self).__init__()

        # Accept drag & drop events
        self.setAcceptDrops(True)

        self.force_quit = False

        # Window title stuff
        self.wt_wordcount = 0
        self.wt_modified = False
        self.wt_file = ''

        # Layout
        main_layout = QtGui.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0,0,0,0)

        top_layout = QtGui.QHBoxLayout()
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0,0,0,0)
        main_layout.addLayout(top_layout)

        # Text area
        self.textarea = LineTextWidget(self)
        self.document = self.textarea.document()
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.textarea.setTabStopWidth(30)
        top_layout.addWidget(self.textarea)
        self.findtext = ''
        self.replace1text = ''
        self.replace2text = ''

        # Terminal
        self.terminal = Terminal(self)
        main_layout.addWidget(self.terminal)
        self.terminal.setVisible(False)
        self.font_dialog_open = False

        # Misc settings etc
        self.filename = ''
        self.blocks = 1
        self.textarea.setContextMenuPolicy(Qt.PreventContextMenu)

        # Signals/slots
        self.connect(self.document, SIGNAL('modificationChanged(bool)'),
                     self.toggle_modified)
        self.connect(self.document, SIGNAL('contentsChanged()'),
                     self.update_word_count)
        self.connect(self.textarea, SIGNAL('blockCountChanged(int)'),
                     self.new_line)

        # Paths init
        system = platform.system()
        if system == 'Linux':
            cfgdir = os.path.join(os.getenv('HOME'), '.config',
                                    'kalpana')
            self.cfgpath = os.path.join(cfgdir, 'kalpana.conf')
        else:
            self.cfgpath = local_path('kalpana.json')

        # Keyboard shortcuts
        hotkeys = {
            'Ctrl+N': self.new,
            'Ctrl+O': self.open_k,
            'Ctrl+S': self.save_k,
            'Ctrl+Shift+S': self.save_as_k,
            'F3': self.find_next,
            'Ctrl+Return': self.toggle_terminal
        }

        hotkeys.update(plugin_hotkeys)

        for key, function in hotkeys.items():
            QtGui.QShortcut(QtGui.QKeySequence(key), self, function)


        # Config
        with open(local_path('defaultcfg.json'), encoding='utf8') as f:
            defaultcfg = json.loads(f.read())

        self.stylesheet_template = None
        self.read_config(defaultcfg)

        if file_:
            if not self.open_file(file_):
                self.close()
            self.update_window_title()
        else:
            self.set_file_name('NEW')

        self.show()


## ==== Overrides ========================================================== ##

    def closeEvent(self, event):
        if not self.document.isModified() or self.force_quit:
            self.write_config()
            event.accept()
        else:
            self.terminal.setVisible(True)
            self.switch_focus_to_term()
            self.terminal.error('Unsaved changes! Force quit with q! or save first.')
            event.ignore()

    def dragEnterEvent(self, event):
##        if event.mimeData().hasFormat('text/plain'):
        event.acceptProposedAction();

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        parsedurls = []
        for u in urls:
            u = u.path()
            if not os.path.isfile(u) and u.startswith('/'):
                u = u[1:]
            parsedurls.append(u)

        for u in parsedurls:
            subprocess.Popen([sys.executable, sys.argv[0], u])
        event.acceptProposedAction();


## ==== Config ============================================================= ##

    def read_config(self, default_config):
        """ Read the config and update the appropriate variables. """

        optionalvalues = ('term_input_bgcolor',
                          'term_output_bgcolor',
                          'term_input_textcolor',
                          'term_output_textcolor')

        def check_config(cfg, defcfg):
            """ Make sure the config is valid """
            out = {}
            for key, defvalue in defcfg.items():
                if key in cfg:
                    if type(defvalue) == dict:
                        out[key] = check_config(cfg[key], defvalue)
                    elif not cfg[key] and key not in optionalvalues:
                        out[key] = defvalue
                    else:
                        out[key] = cfg[key]
                else:
                    out[key] = defvalue
            return out

        try:
            with open(self.cfgpath, encoding='utf-8') as f:
                rawcfg = json.loads(f.read())
        except (IOError, ValueError):
            print('no/bad config')
            cfg = default_config
        else:
            cfg = check_config(rawcfg, default_config)

        # Settings
        self.lastdir = cfg['settings']['lastdirectory']
        vscrollbar = cfg['settings']['vscrollbar']
        if vscrollbar == 'always':
            self.always_show_scrollbar()
        elif vscrollbar == 'needed':
            self.show_scrollbar_when_needed()
        elif vscrollbar == 'never':
            self.never_show_scrollbar()
        self.textarea.number_bar.showbar = cfg['settings']['linenumbers']
        self.autoindent = cfg['settings']['autoindent']
        self.open_in_new_window = cfg['settings']['open_in_new_window']
        self.show_fonts_in_dialoglist = cfg['settings']['show_fonts_in_dialoglist']
        self.guidialogs = cfg['settings']['guidialogs']
        self.start_in_term = cfg['settings']['start_in_term']
        if self.start_in_term:
            self.terminal.setVisible(True)
            self.switch_focus_to_term()

        self.themedict = cfg['theme']

        with open(local_path('qtstylesheet.css'), encoding='utf8') as f:
            self.stylesheet_template = f.read()

        self.update_theme(cfg['theme'])

    def write_config(self):
        """
        Read the config, update the info with appropriate variables (optional)
        and then overwrite the old file with the updated config.
        """
        vscrollbar = ('needed', 'never', 'always')
        sizepos = self.geometry()
        font = self.document.defaultFont()
        cfg = {
            'window': {
                'x': sizepos.left(),
                'y': sizepos.top(),
                'width': sizepos.width(),
                'height': sizepos.height(),
                'maximized': self.isMaximized(),
            },
            'settings': {
                'lastdirectory': self.lastdir,
                'vscrollbar': vscrollbar[self.textarea.
                                    verticalScrollBarPolicy()],
                'linenumbers': self.textarea.number_bar.showbar,
                'autoindent': self.autoindent,
                'open_in_new_window': self.open_in_new_window,
                'show_fonts_in_dialoglist': self.show_fonts_in_dialoglist,
                'guidialogs': self.guidialogs,
                'start_in_term': self.start_in_term,
            },
            'theme': self.themedict
        }

        outjson = json.dumps(cfg, ensure_ascii=False, indent=2, sort_keys=True)
        if not os.path.exists(os.path.dirname(self.cfgpath)):
            os.makedirs(os.path.dirname(self.cfgpath), mode=0o755, exist_ok=True)
            print('Creating config path...')
        with open(self.cfgpath, 'w', encoding='utf-8') as f:
            f.write(outjson)


    def update_theme(self, themedict):
        self.themedict = themedict.copy()

        overload = {
            'term_input_bgcolor': 'main_bgcolor',
            'term_output_bgcolor': 'main_bgcolor',
            'term_input_textcolor': 'main_textcolor',
            'term_output_textcolor': 'main_textcolor',
        }
        for x, y in overload.items():
            if not themedict[x]:
                themedict[x] = themedict[y]
        for value in themedict.values():
            # TODO: no graphical shit!!!
            if not value:
                self.terminal.error('Themesection in the config is broken!')
                break

        self.setStyleSheet(self.stylesheet_template.format(**themedict))

    def reload_theme(self):
        with open(local_path('qtstylesheet.css'), encoding='utf8') as f:
            self.stylesheet_template = f.read()

        with open(self.cfgpath, encoding='utf-8') as f:
            cfg = json.loads(f.read())
        self.update_theme(cfg['theme'])


## ==== Misc =============================================================== ##

    def prompt_error(self, errortext, defaultcmd=''):
        self.terminal.error(errortext)
        self.prompt_term(defaultcmd)

    def prompt_term(self, defaultcmd=''):
        if defaultcmd:
            self.terminal.input_term.setText(defaultcmd)
        self.terminal.setVisible(True)
        self.switch_focus_to_term()


    def toggle_terminal(self):
        self.terminal.setVisible(abs(self.terminal.isVisible()-1))
        if self.terminal.isVisible():
            self.switch_focus_to_term()
        else:
            self.textarea.setFocus()


    def switch_focus_to_term(self):
        self.terminal.input_term.setFocus()


    def new_line(self, blocks):
        """ Generate auto-indentation if the option is enabled. """
        if blocks > self.blocks and self.autoindent:
            cursor = self.textarea.textCursor()
            blocknum = cursor.blockNumber()
            prevblock = self.document.findBlockByNumber(blocknum-1)
            indent = re.match(r'[\t ]*', prevblock.text()).group(0)
            cursor.insertText(indent)


    def new_and_empty(self):
        """ Return True if the file is empty and unsaved. """
        return not self.document.isModified() and not self.filename

    # ---- Vertical scrollbar -------------------------------------- #

    def always_show_scrollbar(self):
        """ Always show the vertical scrollbar. Convenience function. """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def show_scrollbar_when_needed(self):
        """
        Only show the vertical scrollbar when needed.
        Convenience function.
        """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def never_show_scrollbar(self):
        """ Never show the vertical scrollbar. Convenience function. """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    # -------------------------------------------------------------- #


    def find_next(self):
        if not self.findtext:
            self.terminal.error("No previous searches")
            return
        temp_cursor = self.textarea.textCursor()
        found = self.textarea.find(self.findtext)
        if not found:
            if not self.textarea.textCursor().atStart():
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                found = self.textarea.find(self.findtext)
                if not found:
                    self.textarea.setTextCursor(temp_cursor)
                    self.terminal.error('[find] Text not found')


    def replace_next(self):
        if not self.replace1text:
            self.terminal.error("No previous replaces")
            return

        temp_cursor = self.textarea.textCursor()
        found = self.textarea.find(self.replace1text)
        if not found:
            if not self.textarea.textCursor().atStart():
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                found = self.textarea.find(self.replace1text)
                if not found:
                    self.textarea.setTextCursor(temp_cursor)
        if found:
            self.textarea.textCursor().insertText(self.replace2text)
            self.terminal.print_('found sumfin! {0}'.format(self.textarea.textCursor().hasSelection()))
        else:
            self.terminal.error('[replace] Text not found')


    def replace_all(self):
        if not self.replace1text:
            self.terminal.error("No previous replaces")
            return

        temp_cursor = self.textarea.textCursor()
        times = 0
        while True:
            found = self.textarea.find(self.replace1text)
            if found:
                self.textarea.textCursor().insertText(self.replace2text)
                times += 1
            else:
                if self.textarea.textCursor().atStart():
                    break
                else:
                    self.textarea.moveCursor(QtGui.QTextCursor.Start)
                    continue
        if times:
            self.terminal.print_('{0} instances replaced'.format(times))
        else:
            self.textarea.setTextCursor(temp_cursor)
            self.terminal.error('[replace_all] Text not found')


## ==== Window title ===================================== ##

    def update_window_title(self):
        self.setWindowTitle('{0}{1} - {2}{0}'.format('*'*self.wt_modified,
                                                     self.wt_wordcount,
                                                     self.wt_file))


    def toggle_modified(self, modified):
        """
        Toggle the asterisks in the title depending on if the file has been
        modified since last save/open or not.
        """
        self.wt_modified = modified
        self.update_window_title()


    def update_word_count(self):
        wcount = len(re.findall(r'\S+', self.document.toPlainText()))
        if not wcount == self.wt_wordcount:
            self.wt_wordcount = wcount
            self.update_window_title()


    def set_file_name(self, filename):
        """ Set both the output file and the title to filename. """
        if filename == 'NEW':
            self.filename = ''
            self.wt_file = 'New file'
        else:
            self.filename = filename
            self.wt_file = os.path.basename(filename)
        self.update_window_title()



## ==== File operations: new/open/save ===================================== ##

    def new(self, force=False):
        """ Create a new file. Terminal usage """
        if self.open_in_new_window and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0]])
        elif not self.document.isModified() or force:
            self.document.clear()
            self.document.setModified(False)
            self.toggle_modified(False)
            self.set_file_name('NEW')
            self.blocks = 1
        else:
            self.prompt_error('Unsaved changes! Force new with n! or save first.')

    def open_k(self):
        """ Open, called from key shortcut """
        if not self.guidialogs:
            self.prompt_term(defaultcmd='o ')
        else:
            if (self.open_in_new_window or not self.document.isModified()):
                filename = QtGui.QFileDialog.getopen_fileName(self,
                                                      directory=self.lastdir)[0]
                if filename:
                    self.open_t(filename)
            else:
                self.prompt_error('Unsaved changes! Force open with o! or save first.')

    def open_t(self, filename, force=False):
        """ Open, called from terminal """
        if self.open_in_new_window and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0], filename])
        elif not self.document.isModified() or force:
            self.lastdir = os.path.dirname(filename)
            self.open_file(filename)
        else:
            self.prompt_error('Unsaved changes! Force open with o! or save first.')


    def open_file(self, filename):
        encodings = ('utf-8', 'latin1')
        readsuccess = False
        for e in encodings:
            try:
                with open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                readsuccess = True
                self.document.setPlainText(''.join(lines))
                self.document.setModified(False)
                self.set_file_name(filename)
                self.blocks = self.document.blockCount()
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                return True
        if not readsuccess:
            self.terminal.error('File could not be decoded!')
            self.terminal.setVisible(True)
            return False


    def save_k(self):
        """ Called from hotkey when guidialogs is on """
        if not self.filename:
            if self.guidialogs:
                fname = QtGui.QFileDialog.getSaveFileName(self,
                                    directory=self.lastdir)[0]
                if fname:
                    self.save_t(fname)
            else:
                self.prompt_error('File not saved yet! Save with s first.',
                                 defaultcmd='s ')
        else:
            self.save_t()

    def save_as_k(self):
        """ Called from hotkey when guidialogs is on """
        if self.guidialogs:
            fname = QtGui.QFileDialog.getSaveFileName(self,
                                    directory=self.lastdir)[0]
            if fname:
                self.save_t(fname)
        else:
            self.prompt_term(defaultcmd='s ')


    def save_t(self, filename=''):
        if filename:
            savefname = filename
        else:
            savefname = self.filename

        assert savefname.strip() != ''

        try:
            with open(savefname, 'w', encoding='utf-8') as f:
                f.write(self.document.toPlainText())
        except IOError as e:
            print(e)
        else:
            self.lastdir = os.path.dirname(savefname)
            self.set_file_name(savefname)
            self.document.setModified(False)


def local_path(path):
    return os.path.join(sys.path[0], path)


def get_valid_files():
    output = []
    for f in sys.argv[1:]:
        # try:
        #     f = unicode(f, 'utf-8')
        # except UnicodeDecodeError:
        #     f = unicode(f, 'latin1')
        if os.path.isfile(os.path.abspath(f)):
            output.append(f)
        else:
            print('File not found:')
            print(f)
    return output

if __name__ == '__main__':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    files = get_valid_files()
    app = QtGui.QApplication(sys.argv)

    if not files:
        a = MainWindow()
    else:
        a = MainWindow(file_=files[0])
        for f in files[1:]:
            subprocess.Popen([sys.executable, sys.argv[0], f.encode('utf-8')])
    sys.exit(app.exec_())
