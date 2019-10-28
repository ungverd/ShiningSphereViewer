import sys
import os
import csv
import time

from PyQt5 import QtCore, QtGui, QtWidgets

import design

_translate = QtCore.QCoreApplication.translate

FILENAME = 'effect.h'
WIDTH = 9
HEIGHT = 5
ROW_LENGTH = WIDTH * HEIGHT
BLUES = [2, 5, 13, 16, 22, 29, 31, 35, 43]
COLORS = [[(HEIGHT*j+i) in BLUES for j in range(WIDTH)] for i in range(HEIGHT)]

ROW = int('0x18', 16)
PAUSE = int('0x36', 16)
START = int('0x22', 16)
STOP = int('0x23', 16)

class SphereUi(QtWidgets.QMainWindow, design.Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.round = False
        self.stopped = False
        self.re_null()

        self.upd_gen = self.update_gen()

        self.verticalSlider.actionTriggered.connect(self.change_framerate)
        self.RoundCheckBox.stateChanged.connect(self.change_round)
        self.StartStopButton.clicked.connect(self.startstop)
        self.ReloadButton.clicked.connect(self.reload)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_img)
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
                    if rule[2] == 'pause':
                        counter = rule[0]
                        while counter > 0:
                            counter -= 1
                            yield
                    else:
                        self.stack.append(rule[:] + [j])


            while self.stack and self.i == self.stack[-1][2]:
                self.stack[-1][0] -= 1
                if self.stack[-1][0] == 0:
                    self.stack = self.stack[:-1]
                else:
                    self.i = self.stack[-1][1] - 1
                    self.returned = self.stack[-1][3]
                    break

            self.i += 1
            

            '''if self.i >= len(self.frames):
                print('end')'''
            
            if self.i >= len(self.frames):
                self.re_null()
                if not self.round:
                    self.stop()
            yield


    def update_img(self):
        self.draw_frame(self.frames[self.i])

        #update i
        next(self.upd_gen)

    def draw_frame(self, frame):
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if COLORS[i][j]:
                    color = (0, 0, frame[i][j])
                else:
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
        with open (FILENAME, newline='', mode='r') as f:

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
            values = [int(v.strip(), 16) for v in s.split(',')]


            i = 0
            if values[0] == PAUSE:
                empty_frame = [ROW] + [0]*ROW_LENGTH
                values = empty_frame + values
            while i < len(values):
                if values[i] == ROW:
                    row = values[i + 1 : i + ROW_LENGTH + 1]
                    greens = (x for x in row[:-len(BLUES):])
                    blues = (x for x in row[-len(BLUES)::])
                    line = []
                    for j in range(ROW_LENGTH):
                        if j in BLUES:
                            line.append(next(blues))
                        else:
                            line.append(next(greens))
                    frame = [line[j::HEIGHT] for j in range(HEIGHT)]
                    frames.append(frame)
                    i += (ROW_LENGTH + 1)
                elif values[i] == PAUSE:
                    pause_len = values[i+1]

                    if pause_len == 0:
                        pause_len = -1
                    rules.append([pause_len, len(frames)-1, 'pause'])
                    i += 2

                elif values[i] == START:
                    reps = values[i+1]
                    if reps == 0:
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
                    i += 1
                else:
                    raise Exception('incorrect input file')
        self.frames = frames
        self.rules = rules


app = QtWidgets.QApplication(sys.argv)
window = SphereUi()
window.show()
app.exec_()