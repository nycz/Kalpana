# Copyright nycz 2011-2012

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


import os.path
import fontdialog

try:
    from PySide import QtGui
    from PySide.QtCore import Qt, SIGNAL, QDir, QEvent
except ImportError:
    from PyQt4 import QtGui
    from PyQt4.QtCore import Qt, SIGNAL, QDir, QEvent


class Terminal(QtGui.QSplitter):

    class InputBox(QtGui.QLineEdit):
        def __init__(self, *args):
            QtGui.QLineEdit.__init__(self, *args)

        def event(self, event):
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab and\
                        event.modifiers() == Qt.NoModifier:
                self.emit(SIGNAL('tabPressed()'))
                return True
            else:
                return QtGui.QLineEdit.event(self, event)

        def keyPressEvent(self, event):
            if event.text() or event.key() in (Qt.Key_Left, Qt.Key_Right):
                QtGui.QLineEdit.keyPressEvent(self, event)
                self.emit(SIGNAL('updateCompletionPrefix()'))
            elif event.key() == Qt.Key_Up:
                self.emit(SIGNAL('historyUp()'))
            elif event.key() == Qt.Key_Down:
                self.emit(SIGNAL('historyDown()'))
            else:
                return QtGui.QLineEdit.keyPressEvent(self, event)
  
    # This needs to be here for the stylesheet 
    class OutputBox(QtGui.QLineEdit):
        pass


    def __init__(self, main):
        QtGui.QSplitter.__init__(self, parent=main)
        self.textarea = main.textarea
        self.main = main
        self.sugindex = -1

        self.history = []

        # Splitter settings
        self.setHandleWidth(2)

        # I/O fields creation
        self.inputTerm = self.InputBox(self)
        self.outputTerm = self.OutputBox(self)
        self.outputTerm.setDisabled(True)
        self.outputTerm.setAlignment(Qt.AlignRight)

        self.addWidget(self.inputTerm)
        self.addWidget(self.outputTerm)

        # Autocomplete
        self.completer = QtGui.QCompleter(self)
        fsmodel = QtGui.QFileSystemModel(self.completer)
        fsmodel.setRootPath(QDir.homePath())
        self.completer.setModel(fsmodel)
        self.completer.setCompletionMode(QtGui.QCompleter.InlineCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitive)
        
        self.connect(self.inputTerm, SIGNAL('tabPressed()'),
                     self.autocomplete)
        self.connect(self.inputTerm, SIGNAL('updateCompletionPrefix()'),
                     self.updateCompletionPrefix)

        self.connect(self.inputTerm, SIGNAL('returnPressed()'), 
                     self.parseCommand)
        QtGui.QShortcut(QtGui.QKeySequence('Alt+Left'), self,
                        self.moveSplitterLeft)
        QtGui.QShortcut(QtGui.QKeySequence('Alt+Right'), self,
                        self.moveSplitterRight)
    

    # ==== Autocomplete ========================== #

    def getAutocompletableText(self):
        cmds = ('o', 'o!', 's', 's!')
        text = self.inputTerm.text()
        for c in cmds:
            if text.startswith(c + ' '):
                return text[:len(c)+1], text[len(c)+1:]
        return None, None


    def autocomplete(self):
        cmdprefix, ac_text = self.getAutocompletableText()
        if ac_text is None:
            return
    
        separator = QDir.separator()

        # Autocomplete with the working directory if the line is empty
        if ac_text.strip() == '':
            wd = os.path.abspath(self.main.filename)
            if not os.path.isdir(wd):
                wd = os.path.dirname(wd)
            self.completer.setCompletionPrefix(wd + separator)
            self.inputTerm.setText(cmdprefix + wd + separator)
            return

        isdir = os.path.isdir(self.completer.currentCompletion())
        if ac_text == self.completer.currentCompletion() + separator*isdir:
            if not self.completer.setCurrentRow(self.completer.currentRow() + 1):
                self.completer.setCurrentRow(0)

        prefix = self.completer.completionPrefix()
        suggestion = self.completer.currentCompletion()
        newisdir = os.path.isdir(self.completer.currentCompletion())
        self.inputTerm.setText(cmdprefix + prefix + suggestion[len(prefix):] + separator*newisdir)


    def updateCompletionPrefix(self):
        cmdprefix, ac_text = self.getAutocompletableText()
        if not ac_text:
            return
        self.completer.setCompletionPrefix(ac_text)


    # ==== Splitter ============================== #

    def moveSplitter(self, dir):
        s1, s2 = self.sizes()
        jump = int((s1 + s2) * 0.1)
        if dir == 'left':
            new_s1 = max(0, s1 - jump)
        else:
            new_s1 = min(s1 + s2, s1 + jump)
        new_s2 = s1 + s2 - new_s1
        self.setSizes((new_s1, new_s2))

    def moveSplitterLeft(self):
        self.moveSplitter('left')

    def moveSplitterRight(self):
        self.moveSplitter('right')


    # ==== History =============================== #

    def historyUp(self):
        pass
        # if self.historyPosition > 0:
        #     self.historyPosition -= 1:
        #     self.inputTerm.setText(self.history[self.historyPosition])

    def historyDown(self):
        # if self.historyPosition < len(self.history)-1:
        #     self.historyPosition += 1:
        #     self.inputTerm.setText(self.history[self.historyPosition])
        # elif self.historyPosition == len(self.history)-1 and self.inputTerm.text():
        #     self.historyPosition += 1:
        pass


    # ==== Misc ================================= #

    def switchFocus(self):
        self.main.textarea.setFocus()


    def parseCommand(self):
        text = self.inputTerm.text()
        if not text.strip():
            return
        self.history.append(text)
        self.historyPosition = len(self.history)
        self.inputTerm.setText('')
        self.outputTerm.setText('')
        cmd = text.split(' ', 1)[0]
        # If the command exists, run the callback function (a bit cryptic maybe)
        if cmd in self.cmds:
            self.cmds[cmd][0](self, text[len(cmd)+1:])
        # Convenience for help and search: ?cf = ? cf, /lol = / lol
        elif text[0] in ('?', '/'):
            self.cmds[text[0]][0](self, text[1:])
        else:
            self.error('No such function (? for help)')


    def print_(self, text):
        self.outputTerm.setText(str(text))


    def error(self, text):
        self.outputTerm.setText('Error: ' + text)


    # ==== Commands ============================== #
    def cmdOpen(self, arg, force=False):
        f = arg.strip()
        if os.path.isfile(f):
            self.main.open_t(f, force)
        else:
            self.error('Non-existing file')

    def cmdForceOpen(self, arg):
        self.cmdOpen(arg, force=True)


    def cmdNew(self, arg):
        self.main.new_t()

    def cmdForceNew(self, arg):
        self.main.new_t(force=True)


    def cmdSave(self, arg, force=False):
        f = arg.strip()
        if not f:
            if self.main.filename:
                self.main.save_t()
            else:
                self.error('No filename')
        else:
            if os.path.isfile(f) and not force:
                self.error('File already exists, use s! to overwrite')
            # Make sure the parent directory actually exists
            elif os.path.isdir(os.path.dirname(f)):
                self.main.save_t(f)
            else:
                self.error('Invalid path')

    def cmdOverwriteSave(self, arg):
        self.cmdSave(arg, force=True)


    def cmdQuit(self, arg):
        self.main.close()
       
    def cmdForceQuit(self, arg):
        self.main.forcequit = True
        self.main.close()


    def cmdFind(self, arg):
        if arg:
            self.main.findtext = arg
        self.main.findNext()

    def setReplaceTexts(self, arg):
        """ Try to set the find/replace texts to the args, return False if it fails """
        try:
            self.main.replace1text, self.main.replace2text = arg.split(' ', 1)
        except ValueError:
            self.error('Not enough arguments')
            return False
        return True

    def cmdReplace(self, arg):
        if arg and not self.setReplaceTexts(arg):
            return
        self.main.replaceNext()

    def cmdReplaceAll(self, arg):
        if arg and not self.setReplaceTexts(arg):
            return
        self.main.replaceAll()


    def cmdChangeFont(self, arg):
        if self.main.fontdialogopen:
            self.error('Font dialog already open')
            return
        if arg not in ('main', 'term', 'nano'):
            self.error('Wrong argument [main/term/nano]')
            return
        if arg == 'term':
            self.print_('Räksmörgås?!')
        self.main.fontdialogopen = True
        fwin = fontdialog.FontDialog(self.main, self.main.show_fonts_in_dialoglist, 
                                     arg + '_fontfamily', arg + '_fontsize')

    def cmdAutoIndent(self, arg):
        self.main.autoindent = not self.main.autoindent
        self.print_('Now ' + str(self.main.autoindent).lower())

    def cmdLineNumbers(self, arg):
        self.textarea.number_bar.showbar = not self.textarea.number_bar.showbar
        self.textarea.number_bar.update()
        self.print_('Now ' + str(self.textarea.number_bar.showbar).lower())

    def cmdScrollbar(self, arg):
        arg = arg.strip().lower()
        if not arg:
            self.print_(('Off','Maybe','On')[self.textarea.verticalScrollBarPolicy()])
        elif arg == 'off':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elif arg == 'maybe':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        elif arg == 'on':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        else:
            self.error('Wrong argument [off/maybe/on]')

    def cmdNewWindow(self, arg):
        arg = arg.strip()
        if not arg:
            self.print_(self.main.open_in_new_window)
        elif arg == 'y':
            self.main.open_in_new_window = True
        elif arg == 'n':
            self.main.open_in_new_window = False
        else:
            self.error('Wrong argument [y/n]')

    def cmdHelp(self, arg):
        if not arg:
            self.print_(' '.join(sorted(self.cmds)))
        elif arg in self.cmds:
            self.print_(self.cmds[arg][1])
        else:
            self.error('No such command')

    def cmdNanoToggle(self, arg):
        if arg.strip().isdigit():
            if int(arg.strip()) == 0:
                self.main.nanoMode = False
                self.print_('NaNo mode disabled')
            elif int(arg.strip()) in range(1,self.main.days + 1):
                self.main.myDay = int(arg.strip())
                self.main.nanoMode = True
                self.main.nanoCountWordsChapters()
                self.main.myLastWcount = self.main.accWcount
                self.main.nanoExtractOldStats()
                self.main.nanowidget.setPlainText(self.main.nanoGenerateStats())
                self.print_('NaNo mode initiated')
            else:
                self.error('Invalid date')
        else:
            self.error('Invalid argument')

    def cmdReloadTheme(self, arg):
        self.main.reloadTheme()



    cmds = {'o': (cmdOpen, 'Open [file]'),
            'o!': (cmdForceOpen, 'Open [file] and discard the old'),
            'n': (cmdNew, 'Open new file'),
            'n!': (cmdForceNew, 'Open new file and discard the old'),
            's': (cmdSave, 'Save (as) [file]'),
            's!': (cmdOverwriteSave, 'Save (as) [file] and overwrite'),
            'q': (cmdQuit, 'Quit Kalpana'),
            'q!': (cmdForceQuit, 'Quit Kalpana without saving'),
            '/': (cmdFind, 'find (next) [string]'),
            'r': (cmdReplace, 'Replace (syntax help needed)'),
            'ra': (cmdReplaceAll, 'Replace all (syntax help needed)'),
            '?': (cmdHelp, 'List commands or help for [command]'),
            'cf': (cmdChangeFont, 'Change font [main/term/nano]'),
            'ai': (cmdAutoIndent, 'Toggle auto indent'),
            'ln': (cmdLineNumbers, 'Toggle line numbers'),
            'vs': (cmdScrollbar, 'Scrollbar [off/maybe/on]'),
            'nw': (cmdNewWindow, 'Open in new window [y/n]'),
            'nn': (cmdNanoToggle, 'Start NaNo mode at [day]'),
            'rt': (cmdReloadTheme, 'Reload theme from config')}