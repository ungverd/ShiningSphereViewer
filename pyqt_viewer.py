import sys
import os
import csv
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from loguru import logger

import design

_translate = QtCore.QCoreApplication.translate

WIDTH = 9
HEIGHT = 7
ADD_H = 2
OLD_H = HEIGHT - ADD_H
ROW_LENGTH = WIDTH * HEIGHT
BLUES = [2, 5, 13, 16, 22, 29, 31, 35, 43]
COLORS = [[(OLD_H*j+i) in BLUES for j in range(WIDTH)] for i in range(OLD_H)] + ADD_H * [[False] * WIDTH]

ROW = int('0x18', 16)
PAUSE = int('0x36', 16)
START = int('0x22', 16)
STOP = int('0x23', 16)
INFINITE = int('0xff', 16)
ENDFILE = int('0xf1', 16)

class SphereUi(QtWidgets.QMainWindow, design.Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.fname = 'effect.h'

        self.round = False
        self.stopped = False
        self.re_null()

        self.upd_gen = self.update_gen()

        self.verticalSlider.actionTriggered.connect(self.change_framerate)
        self.RoundCheckBox.stateChanged.connect(self.change_round)
        self.StartStopButton.clicked.connect(self.startstop)
        self.ReloadButton.clicked.connect(self.reload)
        self.openFileButton.clicked.connect(self.openFile)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_img)
        self.reload()

    def openFile(self):
        self.fname = QtWidgets.QFileDialog.getOpenFileName(self,
                                                           'Open file', 
                                                           os.path.dirname(os.path.abspath(__file__)),
                                                           '*.h')[0]
        self.reload()

    def reload(self):
        self.get_frames()
        self.re_null()
        self.start()

    def change_framerate(self):
        if not self.stopped:
            framerate = self.verticalSlider.value()
            period = 1000 // framerate
            self.timer.start(period)

    def change_round(self):
        self.round = self.RoundCheckBox.checkState()

    def re_null(self):
        self.i = 0
        self.stack = []
        self.returned = -1

    def update_gen(self):
        while True:
            for j in range(self.returned + 1, len(self.rules)):
                rule = self.rules[j]
                if self.i == rule[1]:
                    self.stack.append(rule[:] + [j])

            if self.frames[self.i][1] == 'pause':
                counter = self.frames[self.i][0]
                while counter > 0:
                    counter -= 1
                    yield #pause here
            else:
                yield #draw frame here


            while self.stack and self.i == self.stack[-1][2]:
                self.stack[-1][0] -= 1
                if self.stack[-1][0] == 0:
                    self.stack.pop()
                else:
                    self.i = self.stack[-1][1] - 1
                    self.returned = self.stack[-1][3]
                    break

            self.i += 1
            
            if self.i >= len(self.frames):
                self.re_null()
                if not self.round:
                    self.stop()
                    yield 'stop'


    def update_img(self):

        #update i
        if next(self.upd_gen) != 'stop':
            self.draw_frame(self.frames[self.i])

    def draw_frame(self, frame):
        if frame[1] == 'pause':
            return

        for i in range(HEIGHT):
            for j in range(WIDTH): #white
                if HEIGHT - i <= ADD_H:
                    color = (frame[i][j], frame[i][j], frame[i][j])
                elif COLORS[i][j]: #blue
                    color = (0, 0, frame[i][j])
                else: #green
                    color = (0, frame[i][j], 0)
                color_strs = tuple(("0" + hex(c)[2:])[-2:] for c in color)
                cell = getattr(self, "label%d_%d" % (i, j))
                cell.setStyleSheet("background-color: #%s%s%s" % color_strs)

    def stop(self):
        self.stopped = True
        self.StartStopButton.setText(_translate("MainWindow", "Старт"))
        self.timer.stop()

    def start(self):
        self.stopped = False
        self.StartStopButton.setText(_translate("MainWindow", "Стоп"))
        self.change_framerate() #start timer

    def startstop(self):
        if self.stopped:
            self.start()
        else:
            self.stop()

    def get_frames(self):
        frames = []
        rules = []
        with open (self.fname, newline='', mode='r') as f:

            from_file_started = False
            from_file_stopped = False
            s = ''
            for line in f:
                if not from_file_stopped:
                    if '{' in line:
                        start = line.index('{') + 1
                        from_file_started = True
                        stop = -1
                    if '}' in line:
                        stop = line.index('}')
                        from_file_stopped = True
                    if from_file_started:
                        if stop != -1:
                            s += line[start:stop]
                        else:
                            s += line[start:]
                        stop = -1
                        start = 0
            values = [v.strip() for v in s.split(',')]
            if values[-1] == '':
                values.pop()
            values = [int(v, 16) for v in values]


            i = 0
            if values[0] == PAUSE:
                empty_frame = [ROW] + [0]*ROW_LENGTH
                values = empty_frame + values
            while i < len(values):
                if values[i] == ROW:
                    row = values[i + 1 : i + ROW_LENGTH + 1]
                    frame = [row[j::HEIGHT] for j in range(HEIGHT)]
                    frames.append(frame)
                    i += (ROW_LENGTH + 1)
                elif values[i] == PAUSE:
                    pause_len = values[i+1]

                    if pause_len == INFINITE:
                        pause_len = -1
                    frames.append([pause_len, 'pause'])
                    i += 2

                elif values[i] == START:
                    reps = values[i+1]
                    if reps == INFINITE:
                        reps = -1
                    rules.append([reps, len(frames)])
                    i += 2

                elif values[i] == STOP:
                    j = len(rules) - 1
                    appended = False
                    while not appended:
                        if len(rules[j]) == 2:
                            rules[j].append(len(frames) - 1)
                            appended = True
                        else:
                            j -= 1
                            if j < 0:
                                raise Exception('there is more "close cycle" commands then "open cycle" or some cycles are closed before opened')
                    i += 1
                elif values[i] == ENDFILE:
                    i = len(values) #end
                else:
                    raise Exception('incorrect input file, value %x in place %d' % (values[i], i))
        for rule in rules:
            if len(rule) == 2:
                raise Exception('source file contains cycles that are not closed properly')

        self.frames = frames
        self.rules = rules

def setup_exception_logging():
    # generating our hook
    # Back up the reference to the exceptionhook
    sys._excepthook = sys.excepthook

    def my_exception_hook(exctype, value, traceback):
        # Print the error and traceback
        logger.exception(f"{exctype}, {value}, {traceback}")
        # Call the normal Exception hook after
        sys._excepthook(exctype, value, traceback)
        # sys.exit(1)

    # Set the exception hook to our wrapping function
    sys.excepthook = my_exception_hook


def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    else:
        return os.path.join(os.path.abspath("."), relative)


@logger.catch
def main():
    setup_exception_logging()
    app = QtWidgets.QApplication(sys.argv)
    window = SphereUi()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
