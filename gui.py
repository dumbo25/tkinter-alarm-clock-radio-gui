#!/usr/bin/env python3

# The alarm clock GUI is written in python3 on a
# raspberry pi 3 running raspbian
#
# Run the program with the command:
#
#    $ python3 gui.py
#
# To exit, type CTRL-c and move the mouse
#
# Use only one tkinter layout manager (grid, place, pack)
# I am using grid. Do not mix them
#
# ??? HDMI mirroring may be causing the screen size to be messed up
#
# gui.py doesn't do anything useful, except to simulate the functioning
# of the alarm clock radio GUI. The other scripts need to be merged into 
# the GUI for it to be useful

import time
from datetime import datetime

import tkinter as tk
# from tkinter import ttk

radioGUI = tk.Tk()
radioGUI.configure(background='black')

# make radioGUI use full screen
# 2.8 PiTFT is 320 x 240
radioGUI.overrideredirect(True)
# {0} = ??, {1} = ??, 0+0 = upper left pixel
radioGUI.geometry("{0}x{1}+0+0".format(radioGUI.winfo_screenwidth(), radioGUI.winfo_screenheight()))
# radioGUI.geometry("320x240+0+0".format(radioGUI.winfo_screenwidth(), radioGUI.winfo_screenheight()))
# radioGUI.rowconfigure(1, minsize=200)

# ??? time and date are not centered
dateRow = 0
dateText = tk.StringVar()
dateLabel = tk.Label(radioGUI, font=('arial', 30, 'bold'), fg='red', bg='black', textvariable=dateText).grid(row=dateRow, columnspan=6)

timeRow = 1
timeText = tk.StringVar()
timeLabel = tk.Label(radioGUI, font=('digital-7', 120), fg='red', bg='black', textvariable=timeText, anchor='n').grid(row=timeRow, columnspan=6)

alarmRow = 2
alarmState = "off"
alarmHour = 6
alarmHourText = tk.StringVar()
alarmHourText.set(str(alarmHour).zfill(2))

alarmMinute = 0
alarmMinuteText = tk.StringVar()
alarmMinuteText.set(str(alarmMinute).zfill(2))

alarmText = tk.StringVar()
alarmLabel = tk.Label(radioGUI, font=('arial', 30), fg='red', bg='black', textvariable=alarmText, anchor='n').grid(row=alarmRow, columnspan=6)
if alarmState == "on":
    alarmText.set(str(alarmHour.zfill(2)) + ":" + str(alarmMinute).zfill(2))
else:
    alarmText.set("no alarm")

def updateDate():
    global dateText
    global timeText

    dt = datetime.now()

    dts = dt.strftime('%A %B %d, %Y')
    dateText.set(dts)

    # without the '\n' the bottom part of the time
    # gets cropped ???
    tts = dt.strftime('%H:%M')
    timeText.set(tts+'\n')

    # update every 2 seconds, should be accurate enough
    radioGUI.after(2000, updateDate)

# Set Alarm Row
# skip first column
setAlarmRow = 4

alarmHourLabel = tk.Label(radioGUI, textvariable=alarmHourText, font=('arial', 30, 'bold'), fg='red', bg='black').grid(row=setAlarmRow, column=1)

def alarmHourPress():
    global alarmHour
    global alarmHourText

    alarmHour += 1
    if alarmHour >= 12:
        alarmHour = 0

    alarmHourText.set(str(alarmHour).zfill(2))


alarmHourImage = tk.PhotoImage(file='/home/pi/radio/images/up.gif')
alarmHourButton = tk.Button(radioGUI, image=alarmHourImage, command=alarmHourPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=setAlarmRow, column=2)

alarmMinuteLabel = tk.Label(radioGUI, textvariable=alarmMinuteText, font=('arial', 30, 'bold'), fg='red', bg='black').grid(row=setAlarmRow, column=3)

def alarmMinutePress():
    global alarmMinute
    global alarmMinuteText

    alarmMinute += 5
    if alarmMinute >= 60:
        alarmMinute = 0

    alarmMinuteText.set(str(alarmMinute).zfill(2))

alarmMinuteImage = tk.PhotoImage(file='/home/pi/radio/images/up.gif')
alarmMinuteButton = tk.Button(radioGUI, image=alarmMinuteImage, command=alarmMinutePress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=setAlarmRow, column=4)

alarmOnImage = tk.PhotoImage(file='/home/pi/radio/images/on.gif')
alarmOffImage = tk.PhotoImage(file='/home/pi/radio/images/off.gif')

def alarmOnOffPress():
    global alarmState
    global alarmButton
    global alarmText

    if alarmState == "on":
        # change from on to off
        alarmState = "off"
        alarmButton.configure(image=alarmOffImage)
        alarmText.set("no alarm")
    else:
        # change from off to on
        alarmState = "on"
        alarmButton.configure(image=alarmOnImage)
        alarmText.set(str(alarmHour).zfill(2) + ":" + str(alarmMinute).zfill(2))

alarmButton = tk.Button(radioGUI, command=alarmOnOffPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
alarmButton.configure(image=alarmOffImage)
alarmButton.grid(row=setAlarmRow, column=5)


# Control Row
controlRow = 5
# ??? mode toggles 2nd, 3rd and 4th buttons
# ??? mode sets: FM, iRadio or Songs
mode = "songs"
songsImage = tk.PhotoImage(file='/home/pi/radio/images/songs.gif')
fmImage = tk.PhotoImage(file='/home/pi/radio/images/fm.gif')
iRadioImage = tk.PhotoImage(file='/home/pi/radio/images/iradio.gif')

def modePress():
    global mode
    global modeButton

    if mode == "songs":
        # change from songs to FM
        mode = "fm"
        modeButton.configure(image=fmImage)
    elif mode == "fm":
        # change from FM to iRadio
        mode = "iradio"
        modeButton.configure(image=iRadioImage)
    else:
        # change from iRadio to songs
        mode = "songs"
        modeButton.configure(image=songsImage)

modeButton = tk.Button(radioGUI, command=modePress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
modeButton.configure(image=songsImage)
modeButton.grid(row=controlRow, column=0)


# ??? play and stop toggle states
stopImage = tk.PhotoImage(file='/home/pi/radio/images/stop.gif')
playImage = tk.PhotoImage(file='/home/pi/radio/images/play.gif')
playState = "off"

def playStopPress():
    global mode
    global playState
    global playStopButton

    # songs and iRadio use same buttons
    if playState == "on":
        # change from on to off
        playState = "off"
        playStopButton.configure(image=playImage)
    else:
        # change from off to on
        playState = "on"
        playStopButton.configure(image=stopImage)

playStopButton = tk.Button(radioGUI, command=playStopPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
playStopButton.configure(image=playImage)
playStopButton.grid(row=controlRow, column=1)

def backPress():
    i=2

backImage = tk.PhotoImage(file='/home/pi/radio/images/back.gif')
backButton = tk.Button(radioGUI, image=backImage, command=backPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=2)

def nextPress():
    i=2

nextImage = tk.PhotoImage(file='/home/pi/radio/images/next.gif')
nextButton = tk.Button(radioGUI, image=nextImage, command=nextPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=3)

def volumeUpPress():
    i=2

volumeUpImage = tk.PhotoImage(file='/home/pi/radio/images/volumeup.gif')
volumeUpButton = tk.Button(radioGUI, image=volumeUpImage, command=volumeUpPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=4)

def volumeDownPress():
    i=2

volumeDownImage = tk.PhotoImage(file='/home/pi/radio/images/volumedown.gif')
volumeDownButton = tk.Button(radioGUI, image=volumeDownImage, command=volumeDownPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=5)

##########

updateDate()

radioGUI.mainloop()
