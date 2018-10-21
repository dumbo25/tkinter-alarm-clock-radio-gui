#!/usr/bin/env python3

#########################
#
# acr.py is a python3 script using tkinter, mpd and mpc and crontab
# to create an alarm clock radio. The radio can play music from :
# three sources:
#    broadcast FM radio
#    songs stored on the Raspberry Pi
#    streaming internet radio stations
#
# Start the script running using:
#    python3 acr.py
#
# acr.py was tested on a Raspberry Pi 3 model B+ running raspbian
#
# raspbian stretch comes with smbus, wiringPi and i2cdetect installed
# by default
#
# This script requires the following:
#
#    $ sudo apt-get install mpc mpd -y
#    $ sudo apt-get alsa -y
#
#    HiFiBerry AMP 2 top board, barrel power supply and Speaker
#
#    A 2.8 (320x240) PiTFT capacitive touch screen is used for
#    the main display. The PiTFT has four tactile buttons.
#
#    alsamixer is used to set the digital volume to 20%
#
#    I copied my iTunes Library in m4a format to /home/pi/Music
#       iTunes creates folders by artist and then by album
#       In a MacBook Finder window I searched music library for
#       *.m4a. I selected all of those m4a files and copied them
#       to a temp folder and then scp'd all of those from the
#       MacBook to Raspberry Pi
#
#       Open a MacBook terminal window cd to the temp directory
#       and run:
#
#          $ scp * pi@<your-hostname>:Music/.
#
#    Finding working internet radio stations is difficult. The general idea
#    is to find m3u file types. Copy the m3u to stations and then validate
#    whether or not they work
#
#    Create /home/pi/Stations directory on MacBook. Copy m3u files from the
#    internet. The difficulty seems to be in finding streaming stations that
#    work. Here are some good sources:
#       http://dir.xiph.org/by_genre/Rock
#
#    Copy or download the m3us from the sources above to MacBook. Copy the
#    m3u files
#       $ scp * pi@<your-hostname>:Stations/.
#
#    FM radio needs an LM386 FM breakout board and its own analog amplifier.
#
#       Icstation LM386 Mini Mono Audio Amplifier Power Amp Module 5V-12V
#
#       The HiFiBerry AMP 2 does not have an analog input for the FM
#       receiver
#
#    Important files on the Raspberry Pi:
#
#       Config files:
#          /etc/mpd.conf
#          /etc/asounf.conf
#          /use/share/alsa/alsa.conf
#          /home/pi/radio/acr.conf
#
#       Logs are stored here:
#          /var/log/mpd/mpd.log
#          /home/pi/radio/acr.log
#
#       mpd song playlists are different than streaming radio station
#       playlists. Playlists are stored here:
#          /var/lib/mpd/playlists
#          /home/pi/Stations/playlists
#
#       Songs and Staions are stored here:
#          /home/pi/Music
#          /home/pi/Stations
#
#       commands to control/examine mpd service
#          $ sudo service mpd stop
#          $ sudo service mpd start
#          $ sudo service --status-all | grep mpd
#
#       details of the mpc and mpd commands
#          man mpd
#          man mpc
#
#       MPD playlists won't work for streaming radio:
#          created a data structure to store a streaming playlist
#          mpd only keeps the stream. Want to search on the description
#
# Use only one tkinter layout manager. Pick one of: grid, place or pack
# This script uses tkinter's grid manager. Do not mix the layout managers
#
# crontab's time and date fields are:
#   minute hour dom month dow
#      minute: 0-59
#      hour:   0-23
#      dom: day of month: 1-31
#      month: 1-12 (or names, see below)
#      dow: day of week: 0-7 (0 or 7 is Sun, or use three letter names)
#
#   Use the first three letters of the particular day or month
#   (case doesn't matter). A field may be an asterisk (*), which
#   is ignored
#
#   Add slash /n to repeat every n months/days/hours/minutes
#   Use comma to specify multiples 0 5 * * 1,2,3,4,5 to run alarm
#   every business day
#
# More about the FM Radio:
#   An Si4703 breakout board is connected to a Raspberry Pi 3
#   as follows:
#
#      Si4703         Raspberry Pi 3
#      Pin Name       Pin Name
#      1   3.3v       1   3.3v
#      2   Ground     9   Ground
#      3   SDA/SDIO   3   I2C SDA (GPIO2)
#      4   SCLK       5   I2C SCL (GPIO3)
#      6   RST        34  GPIO16
#
#      Note: there are multiple Si4703 breakout boards and pin outs differ
#
#   The original FM radio script is from:
#      Author: KansasCoder
#      Source: https://www.raspberrypi.org/forums/viewtopic.php?t=28920
#      Fri Dec 20, 2013 9:16 pm
#
#      PiFlyer found a way to flip back to alt0 mode
#
# Three question (???) marks indicate features requiring more work
#
# To Do List:
#    ??? merge fmPlayer.py
#    ??? add song or stream name playing to radioGUI
#    ??? add motion sensor to turn backlight on
#    ??? bottom of time in digital-7 font gets clipped unless "\n"
#        is added. There is a way to not have this happen. height?
#    ??? is there a way to get faster mpd song load, or display
#        loading songs note
#
# Notes:
#    If music file name contains a backquote, you will get error
#    message:
#       EOF in backquote substitution
#
#    This script is a merge of several individual scripts: songPlayer.py,
#    streamPlay.py, fmPlayer.py, alarm.py, gui.py. The individual scripts
#    have more features than the GUI does. The extra code is here in case
#    more features are needed in the future. For example, the scripts support
#    adding or deleting songs, creating playlists and switching playlists
#    and this script does not support those features. The other scripts can
#    be used to set the alarm clock radio.
#
#########################

#########################
import time
import datetime
import os
import sys
import subprocess
import tkinter as tk
from crontab import CronTab
import RPi.GPIO as GPIO
import smbus

#########################
# Global Constants

# Global FM Radio Constants
#   BCM pin numbers
RST = 16
SDA = 2

#   Register Descriptions
DEVICEID = 0x00
CHIPID = 0x01
POWERCFG = 0x02
CHANNEL = 0x03
SYSCONFIG1 = 0x04
SYSCONFIG2 = 0x05
SYSCONFIG3 = 0x06
OSCILLATOR = 0x07
STATUSRSSI = 0x0A
READCHAN = 0x0B
RDSA = 0x0C
RDSB = 0x0D
RDSC = 0x0E
RDSD = 0x0F

#   Si4703 Address
#     Need to find the address of the Si4703
#     This is a bit complicated, because the output won't show
#     correctly until it works. The command to run is:
#
#       $ i2cdetect -y 1
SI4703_Address = 0x10

# FM stations are specified without the dot, so 94.7 is 947
DefaultRadioStation = 947


#########################
# Global Variables
fileLog = open('/home/pi/radio/acr.log', 'w+')
currentStationConfig = '/home/pi/radio/streamPlayer.conf'
tempStationFile = '/home/pi/radio/streamPlayer.tmp'
allStationsFile = '/home/pi/Stations/playlists/all_stations.m3u'

directoryStations = "/home/pi/Stations"
directoryStationsPlaylist = "/home/pi/Stations/playlists"

defaultVolume = 60
currentVolume = defaultVolume
fmVolume = 0

muteVolume = False

my_cron = CronTab(user='pi')
alarms = []

# Buttons on 2.8 capacitive touch PiTFT
channel_list = [17, 22, 23, 27]
backlightOn = True

# set GPIO mode for buttons
GPIO.setmode(GPIO.BCM)

# initialize GPIO pins for buttons
GPIO.setup(channel_list, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# setup backlight GPIO
GPIO.setup(12, GPIO.OUT)
backlight = GPIO.PWM(12, 1000)
backlight.start(100)

# Global song variables
currentSongConfig = '/home/pi/radio/acr.conf'
tempSongFile = '/home/pi/radio/acr.tmp'

directoryMusic = "/home/pi/Music"

# mpd doesn't remember the current playlist
# so, mpc has no way to retrieve it
# if mpc commands are run outside of this script, then there is
# no way to find if the playlist changed
defaultPlaylist = "all_songs"
currentPlaylist = defaultPlaylist

defaultStationPlaylist = "all_stations"
currentStationPlaylist = defaultPlaylist

# Instead of starting with the first song every time, remember
# last song played or get current song playing and start playing it
currentSong = ""

# data structure to store radio stations: station, brief, long and stream
# mpd doesn't store enough meaningful information in the playlist
stationList = list()

# Instead of starting with the first station every time, remember last station
# played or get current station playing and start playing it
# currentStation is an index into stationList
currentStation = ""
cStation = 0

# On mpc commands like play, prev and next, mpc outputs a line
# similar to:
#
#    volume: n/a repeat: off random: off single: off consume: off
#
# adding the following to any mpc command suppresses that output
limitMPCoutput = " | grep \"[-,'[']\""

# FM Radio global variables
#   what is this used for ???
z = "000000000000000"

#   create #create 16 registers for SI4703
reg = [int(0)] * 16

#   create list to write registers
#   only need to write registers 2-7 and since first byte is in the write
#   command then only need 11 bytes to write
writereg = [int(0)] * 11

#   read 32 bytes
readreg = [int(0)] * 32

#   My favorite stations in Austin, TX
FavoriteFmStations=[937, 947, 955, 1023, 1035]
#   start with FM station 947
fmIndex = 1
maxFmIndex = 4

#########################
# Global tkinter GUI variables

# radioGUI is the main tkinter window
# radioGUI has 6 columns and 6 rows, numbered 0..5
radioGUI = tk.Tk()
# radioGUI.pack_propagate(0)

# Since the alarm clock will be used in a bedroom at night, the
# background and color scheme should be easily readable at night
# while not being too bright. While buttons are bright, backlight
# shuts off after a short period
radioGUI.configure(background='black')

# make radioGUI use full screen
radioGUI.overrideredirect(True)
radioGUI.geometry("{0}x{1}+0+0".format(radioGUI.winfo_screenwidth(), radioGUI.winfo_screenheight()))

# Global tkinter widget variables
dateRow = 0
dateText = tk.StringVar()
dateLabel = tk.Label(radioGUI, font=('arial', 30, 'bold'), fg='red', bg='black', textvariable=dateText)
dateLabel.grid(row=dateRow, columnspan=6)

timeRow = dateRow + 1
timeText = tk.StringVar()
timeLabel = tk.Label(radioGUI, font=('digital-7', 120), fg='red', bg='black', textvariable=timeText, anchor='n')
# these don't fix need \n issue
#    radioGUI.pack_propagate(0)
#    filling a column with a blank using arial font
#    radioGUI.config(height=140)
#    radioGUI.rowconfigure(timeRow, weight=1)
# height=2 can work with no \n, but uses too much space
# timeLabel.config(height=2)
timeLabel.grid(row=timeRow, columnspan=6)
# pady can work with no \n but uses space above time
timeLabel.configure(pady=30)

songRow = timeRow + 1
songText = tk.StringVar()
songLabel = tk.Label(radioGUI, font=('arial', 20), fg='red', bg='black', textvariable=songText, anchor='s')
songLabel.grid(row=songRow, columnspan=6)
songText.set(" ")

alarmRow = songRow + 1
alarmHour = 6
alarmHourText = tk.StringVar()
alarmHourText.set(str(alarmHour).zfill(2))

alarmMinute = 0
alarmMinuteText = tk.StringVar()
alarmMinuteText.set(str(alarmMinute).zfill(2))

alarmText = tk.StringVar()
alarmLabel = tk.Label(radioGUI, font=('arial', 30), fg='red', bg='black', textvariable=alarmText, anchor='n')
alarmLabel.grid(row=alarmRow, columnspan=6)

alarmState = "off"
alarmText.set("no alarm")

# event handler to toggle the TFT backlight
def toggleBacklight(channel):
    global backlightOn

    if backlightOn:
        backlightOn = False
        backlight.start(0)
    else:
        backlightOn = True
        backlight.start(100)

# PiTFT Button 17 toggles backlight on and off
GPIO.add_event_detect(17, GPIO.FALLING, callback=toggleBacklight, bouncetime=200)

# event handler to reboot the Raspberry Pi
def reboot(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo reboot"
        subprocess.call(cmd, shell=True)

# PiTFT Button 23 reboots the Raspberry Pi
GPIO.add_event_detect(23, GPIO.FALLING, callback=reboot, bouncetime=200)

# event handler to shutdown the Raspberry Pi
def shutdown(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo shutdown -h 0"
        subprocess.call(cmd, shell=True)

# PiTFT Button 27 shuts down the Raspberry Pi
GPIO.add_event_detect(27, GPIO.FALLING, callback=shutdown, bouncetime=200)

# event handler to exit the script
def exitButtonPress(channel):
    global radioGUI

    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)

    radioGUI.quit()

# PiTFT Button 22 exits this script
GPIO.add_event_detect(22, GPIO.FALLING, callback=exitButtonPress, bouncetime=200)

def songPlaying():
    song = " "
    if mode == "songs":
        f = tempSongFile
        cmd = "mpc current > " + f
        subprocess.call(cmd, shell=True)
        try:
            fileSong = open(f, 'r')
            songAndTitle = fileSong.readline()
            i = songAndTitle.find("-") + 2
            songAndNewline = songAndTitle[i:]
            song = songAndNewline.rstrip()
            fileSong.close()
        except Exception as ex:
            song = ""

    if mode == "iradio":
        song = stationList[cStation][1]

    if mode == "fm":
        s = FavoriteFmStations[fmIndex] / 10.0
        song = str(s)

    return song

# GUI code
def updateDate():
    global dateText
    global timeText

    dt = datetime.datetime.now()

    dts = dt.strftime('%A %B %d, %Y')
    dateText.set(dts)

    # without the '\n' the bottom part of the time
    # gets cropped ???
    tts = dt.strftime('%H:%M')
    # timeText.set(tts+'\n')
    timeText.set(tts)

    # update every 2 seconds, should be accurate enough
    radioGUI.after(2000, updateDate)

    # add songText.set to currently playing song
    s = songPlaying()
    songText.set(s)

# Set Alarm Row
# skip first column
setAlarmRow = alarmRow + 1

def readAlarms():
    global alarms

    # clear out the data structure
    alarms = []

    # read alarms from crontab and build data structure
    i = 0
    for job in my_cron:
        c = str(job.comment)
        if c.startswith('alarm'):
            j = str(job)
            alarms.append(j)
            i += 1
    return

def removeAllAlarms():
    global alarms

    # next remove all alarms
    for a in alarms:
        s = a.find('# alarm')
        if s > 0:
            s += 2 # skip the # and space
            c = a[s:]
            my_cron.remove_all(comment=c)
            my_cron.write()
    return

def removeAlarm(n):
    global alarms

    # if an alarm is removed from the middle of crontab, then the alarm numbering is messed up
    # all alarms must be removed and re-read

    # first remove requested alarm
    c = 'alarm' + str(n)
    my_cron.remove_all(comment=c)
    my_cron.write()

    readAlarms()

    # next remove all alarms from crontab keeping the data structure
    removeAllAlarms()

    # then put all alarms back into crontab with new numbers
    i = 0
    for a in alarms:
        s = a.find('# alarm')
        if s > 0:
            j = a[:s]
            c = 'alarm' + str(i)
            job = my_cron.new(command='/usr/bin/mpc play', comment=c)
            i += 1
            # get crontab times
            t = a.find('/')
            t1 = a[:t]
            l1 = t1.split(" ")
            t2 = []
            j = 0
            for l in l1:
                if l != '':
                    if l.find("-") > 0:
                        t2.append(l)
                    else:
                        t2.append(l)
                    j += 1
            job.setall(t2[0], t2[1], t2[2], t2[3], t2[4])
            my_cron.write()

    readAlarms()

def setAlarm(h, m, dow):
    global alarms
    global currentVolume

    c = 'alarm' + str(len(alarms))
    cmd = '/usr/bin/mpc play; '
    # need to escape % because it is a special character in crontab
    cmd += "/usr/bin/amixer set Digital " + str(currentVolume) + "\%"
    job = my_cron.new(command=cmd, comment=c)
    if int(m) == 0:
        m = '*'
    job.setall(m, h, '*', '*', dow)
    my_cron.write()

    alarms = []
    readAlarms()
    return


alarmHourLabel = tk.Label(radioGUI, textvariable=alarmHourText, font=('arial', 30, 'bold'), fg='red', bg='black')
alarmHourLabel.grid(row=setAlarmRow, column=1)

def alarmHourPress():
    global alarmHour
    global alarmHourText

    alarmHour += 1
    if alarmHour >= 12:
        alarmHour = 0

    alarmHourText.set(str(alarmHour).zfill(2))


alarmHourImage = tk.PhotoImage(file='/home/pi/radio/images/up.gif')
alarmHourButton = tk.Button(radioGUI, image=alarmHourImage, command=alarmHourPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
alarmHourButton.grid(row=setAlarmRow, column=2)

alarmMinuteLabel = tk.Label(radioGUI, textvariable=alarmMinuteText, font=('arial', 30, 'bold'), fg='red', bg='black')
alarmMinuteLabel.grid(row=setAlarmRow, column=3)

def alarmMinutePress():
    global alarmMinute
    global alarmMinuteText

    alarmMinute += 5
    if alarmMinute >= 60:
        alarmMinute = 0

    alarmMinuteText.set(str(alarmMinute).zfill(2))

alarmMinuteImage = tk.PhotoImage(file='/home/pi/radio/images/up.gif')
alarmMinuteButton = tk.Button(radioGUI, image=alarmMinuteImage, command=alarmMinutePress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
alarmMinuteButton.grid(row=setAlarmRow, column=4)

alarmOnImage = tk.PhotoImage(file='/home/pi/radio/images/on.gif')
alarmOffImage = tk.PhotoImage(file='/home/pi/radio/images/off.gif')

def alarmOnOffPress():
    global alarmState
    global alarmButton
    global alarmText
    global currentVolume

    if alarmState == "on":
        # change from on to off
        alarmState = "off"
        alarmButton.configure(image=alarmOnImage)
        alarmText.set("no alarm")

        # clear alarm (clears all alarms)
        # for now only one alarm is supported
        removeAllAlarms()
    else:
        # change from off to on
        alarmState = "on"
        alarmButton.configure(image=alarmOffImage)
        alarmText.set(str(alarmHour).zfill(2) + ":" + str(alarmMinute).zfill(2))

        dow ='*'
        setAlarm(alarmHour, alarmMinute, dow)

alarmButton = tk.Button(radioGUI, command=alarmOnOffPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
if alarmState == "on":
    alarmButton.configure(image=alarmOffImage)
else:
    alarmButton.configure(image=alarmOnImage)
alarmButton.grid(row=setAlarmRow, column=5)


# Control Row
controlRow = setAlarmRow + 1
# mode sets: FM, iRadio or Songs
mode = "songs"
songsImage = tk.PhotoImage(file='/home/pi/radio/images/songs.gif')
fmImage = tk.PhotoImage(file='/home/pi/radio/images/fm.gif')
iRadioImage = tk.PhotoImage(file='/home/pi/radio/images/iradio.gif')

def modePress():
    global mode
    global modeButton
    global playState
    global fmVolume
    global fmIndex

    # when changing mode, stop and change states accordingly
    playState = "off"
    cmd = 'mpc stop'
    subprocess.call(cmd, shell=True)
    # ??? don't know if this is required
    # cmd = 'mpc clear'
    # subprocess.call(cmd, shell=True)
    playStopButton.configure(image=playImage)

    old_mode = mode
    if old_mode == "songs":
        # change from songs to FM
        mode = "fm"
        modeButton.configure(image=fmImage)

        cmd = "mpc stop " + limitMPCoutput
        subprocess.call(cmd, shell=True)

        initFM()

        s = FavoriteFmStations[fmIndex]
        printMsg("station = " + str(s))
        changeFmChannel(s)
        fmVolume = 0
        setFmVolume(fmVolume)

    if old_mode == "fm":
        # change from FM to iRadio
        fmVolume = 0
        setFmVolume(fmVolume)

        # change from FM to iRadio
        mode = "iradio"
        modeButton.configure(image=iRadioImage)
        initStation()

    if old_mode == "iradio":
        # change from iRadio to songs
        mode = "songs"
        modeButton.configure(image=songsImage)

        initPlaylist(defaultPlaylist)
        # initSong()

modeButton = tk.Button(radioGUI, command=modePress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
modeButton.configure(image=songsImage)
modeButton.grid(row=controlRow, column=0)


# play and stop toggle states
stopImage = tk.PhotoImage(file='/home/pi/radio/images/stop.gif')
playImage = tk.PhotoImage(file='/home/pi/radio/images/play.gif')
playState = "off"

def playStopPress():
    global mode
    global playState
    global playStopButton
    global fmVolume

    # songs and iRadio use same buttons
    if playState == "on":
        # change from on to off
        playState = "off"
        playStopButton.configure(image=playImage)
        if mode == "fm":
            fmVolume = 0
            setFmVolume(fmVolume)
        else:
            cmd = "mpc stop " + limitMPCoutput
            subprocess.call(cmd, shell=True)
    else:
        # change from off to on
        playState = "on"
        playStopButton.configure(image=stopImage)
        if mode == "fm":
            fmVolume = 7
            setFmVolume(fmVolume)

            s = FavoriteFmStations[fmIndex]
            changeFmChannel(s)
        else:
            cmd = "mpc play" + limitMPCoutput
            subprocess.call(cmd, shell=True)

playStopButton = tk.Button(radioGUI, command=playStopPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
playStopButton.configure(image=playImage)
playStopButton.grid(row=controlRow, column=1)


def backPress():
    global mode
    global fmIndex

    if mode == "songs":
        cmd = "mpc prev " + limitMPCoutput
        subprocess.call(cmd, shell=True)

    if mode == "iradio":
        incrementCurrentStation(-1)
        switchStation(int(cStation))

    if mode == "fm":
        fmIndex -= 1
        if fmIndex < 0:
            fmIndex = maxFmIndex
        s = FavoriteFmStations[fmIndex]
        changeFmChannel(s)

backImage = tk.PhotoImage(file='/home/pi/radio/images/back.gif')
backButton = tk.Button(radioGUI, image=backImage, command=backPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
backButton.grid(row=controlRow, column=2)

def nextPress():
    global mode
    global fmIndex

    printMsg("nextPress with mode = [" + mode + "]")
    if mode == "songs":
        cmd = "mpc next " + limitMPCoutput
        subprocess.call(cmd, shell=True)

    if mode == "iradio":
        incrementCurrentStation(1)
        switchStation(int(cStation))

    if mode == "fm":
        fmIndex += 1
        if fmIndex > maxFmIndex:
            fmIndex = 0
        s = FavoriteFmStations[fmIndex]
        changeFmChannel(s)

nextImage = tk.PhotoImage(file='/home/pi/radio/images/next.gif')
nextButton = tk.Button(radioGUI, image=nextImage, command=nextPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
nextButton.grid(row=controlRow, column=3)


def volumeUpPress():
    global currentVolume
    global fmVolume

    # volume up
    if mode == "fm":
        fmVolume += 1
        setFmVolume(fmVolume)
    else:
        currentVolume +=5
        if currentVolume > 100:
            currentVolume = 100
        cmd = "amixer set Digital " + str(currentVolume) + "%"
        subprocess.call(cmd, shell=True)

volumeUpImage = tk.PhotoImage(file='/home/pi/radio/images/volumeup.gif')
volumeUpButton = tk.Button(radioGUI, image=volumeUpImage, command=volumeUpPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=4)


def volumeDownPress():
    global currentVolume
    global fmVolume

    # volume down
    if mode == "fm":
        fmVolume -= 1
        setFmVolume(fmVolume)
    else:
        currentVolume -=5
        if currentVolume < 0:
            currentVolume = 0
        cmd = "amixer set Digital " + str(currentVolume) + "%"
        subprocess.call(cmd, shell=True)

volumeDownImage = tk.PhotoImage(file='/home/pi/radio/images/volumedown.gif')
volumeDownButton = tk.Button(radioGUI, image=volumeDownImage, command=volumeDownPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
volumeDownButton.grid(row=controlRow, column=5)


#########################
# Log messages should be time stamped
def timeStamp():
    t = time.time()
    s = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S - ')
    return s

# Write messages in a standard format
def printMsg(s):
    fileLog.write(timeStamp() + s + "\n")

def lastStation(): 
    f = tempStationFile
    cmd = "mpc current > " + f
    subprocess.call(cmd, shell=True)
    try:
        fileStation = open(f, 'r')
        stream = fileStation.readline()
        stream = stream.rstrip()
        fileStation.close()
    except Exception as ex:
        printMsg("Exception in lastStation = [" + ex + "]")
        stream = ""

    return stream

def writeFmRegisters():
    # starts writing at register 2
    # but first byte is in the i2c write command
    global writereg
    global reg
    global readreg

    cmd, writereg[0] = divmod(reg[2], 1<<8)
    writereg[1], writereg[2] = divmod(reg[3], 1<<8)
    writereg[3], writereg[4] = divmod(reg[4], 1<<8)
    writereg[5], writereg[6] = divmod(reg[5], 1<<8)
    writereg[7], writereg[8] = divmod(reg[6], 1<<8)
    writereg[9], writereg[10] = divmod(reg[7], 1<<8)
    w6 = i2c.write_i2c_block_data(SI4703_Address, cmd, writereg)
    readreg[16] = cmd #readreg
    readFmRegisters()
    return

def readFmRegisters():
    global readreg
    global reg

    readreg = i2c.read_i2c_block_data(SI4703_Address, readreg[16], 32)
    reg[10] = int(readreg[0] * 256 + readreg[1])
    reg[11] = int(readreg[2] * 256 + readreg[3])
    reg[12] = int(readreg[4] * 256 + readreg[5])
    reg[13] = int(readreg[6] * 256 + readreg[7])
    reg[14] = int(readreg[8] * 256 + readreg[9])
    reg[15] = int(readreg[10] * 256 + readreg[11])
    reg[0] = int(readreg[12] * 256 + readreg[13])
    reg[1] = int(readreg[14] * 256 + readreg[15])
    reg[2] = int(readreg[16] * 256 + readreg[17])
    reg[3] = int(readreg[18] * 256 + readreg[19])
    reg[4] = int(readreg[20] * 256 + readreg[21])
    reg[5] = int(readreg[22] * 256 + readreg[23])
    reg[6] = int(readreg[24] * 256 + readreg[25])
    reg[7] = int(readreg[26] * 256 + readreg[27])
    reg[8] = int(readreg[28] * 256 + readreg[29])
    reg[9] = int(readreg[30] * 256 + readreg[31])
    return

def getFmChannel():
    readFmRegisters()
    channel = reg[READCHAN] & 0x03FF
    channel *= 2
    channel += 875
    return channel

def changeFmChannel(newchannel):
    c = str(float(newchannel) / 10.0)
    if newchannel < 878 or newchannel > 1080:
        printMsg("  invalid FM channel " + c)
        return
    global reg
    newchannel *= 10
    newchannel -= 8750
    newchannel = int(newchannel / 20)
    readFmRegisters()
    reg[CHANNEL] &= 0xFE00;     # Clear out the channel bits
    reg[CHANNEL] |= newchannel; # Mask in the new channel
    reg[CHANNEL] |= (1<<15);    # Set the TUNE bit to start
    writeFmRegisters()
    time.sleep(1)
    # Try ten times and then fail
    for i in range(0, 9):
        readFmRegisters()
        time.sleep(1)
        if ((reg[STATUSRSSI] & (1<<14)) != 0):
            reg[CHANNEL] &= ~(1<<15)
            writeFmRegisters()
            return

    printMsg("  no signal detected for FM channel " + c)
    return

def setFmVolume(volume):
    global reg
    if volume > 15:
        volume = 15
    if volume < 0:
        volume = 0
    readFmRegisters()
    reg[SYSCONFIG2] &= 0xFFF0   # Clear volume bits
    reg[SYSCONFIG2] = int(volume) # Set volume to lowest
    writeFmRegisters()
    return


def readStreamPlayerConfig():
    global currentStation
    global currentVolume
    global currentStationPlaylist

    stream = lastStation()

    try:
        f = open(currentStationConfig, 'r')
        stream2 = f.readline()
        if stream2 == "":
            currentStation = stream
        else:
            currentStation = stream2.rstrip()

        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentStationPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readStreamPlayerConfig [" + ex + "]")
        currentStation = ""
        currentVolume = defaultVolume
        currentStationPlaylist = defaultStationPlaylist
        f.close()

    printMsg("read streamPlayer config")
    printMsg(" stream = [" + currentStation + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentStationPlaylist + "]")

    cmd = "rm " + tempStationFile
    subprocess.call(cmd, shell=True)
    return

def incrementCurrentStation(i):
    global stationList
    global cStation

    last = len(stationList)
    cStation = cStation + i

    if cStation < 0:
        cStation = 0
    if cStation >= last:
        cStation = last-1

def switchStation(station):
    global stationList

    last = len(stationList)
    if station < 0:
        station = 0
    if station >= last:
        station = last-1

    cmd = 'mpc clear'
    subprocess.call(cmd, shell=True)

    stream = stationList[station][3]
    printMsg("Station = " + stationList[station][0] + ", " + stationList[station][1])
    cmd = 'mpc insert "' + stream + '"' + limitMPCoutput
    subprocess.call(cmd, shell=True)

    cmd = "mpc play "  + limitMPCoutput
    subprocess.call(cmd, shell=True)

def writeStationPlayerTxt():
    global currentStation

    # current stream can be null
    o = subprocess.check_output("mpc current", shell=True)
    stream = o.decode("utf-8")
    if stream != "":
        stream = stream.rstrip()

    currentStation = stream

    f = open(currentStationConfig, 'w')
    f.write(currentStation + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentStationPlaylist + "\n")
    f.close()

def lastSong():
    f = tempSongFile
    cmd = "mpc current > " + f
    subprocess.call(cmd, shell=True)
    try:
        fileSong = open(f, 'r')
        songAndTitle = fileSong.readline()
        i = songAndTitle.find("-") + 2
        songAndNewline = songAndTitle[i:]
        song = songAndNewline.rstrip()
        fileSong.close()
    except Exception as ex:
        printMsg("Exception in lastSong = [" + ex + "]")
        song = ""

    return song

def readACRConfig():
    global currentSong
    global currentVolume
    global currentPlaylist

    song = lastSong()

    try:
        f = open(currentSongConfig, 'r')
        songAndTitle = f.readline()
        if song == "":
            st = songAndTitle.rstrip()
            i = st.find("-") + 2
            song = st[i:]

        currentSong = song
        l = f.readline()
        v = l.rstrip()
        currentVolume = int(v)
        l = f.readline()
        currentPlaylist = l.rstrip()
        f.close()
    except Exception as ex:
        printMsg("Exception in readACRConfig [" + ex + "]")
        currentSong = ""
        currentVolume = defaultVolume
        currentPlaylist = defaultPlaylist
        f.close()

    printMsg("read songPlayer config")
    printMsg(" song = [" + currentSong + "]")
    printMsg(" volume = [" + str(currentVolume) + "]")
    printMsg(" playlist = [" + currentPlaylist + "]")

    cmd = "rm " + tempSongFile
    subprocess.call(cmd, shell=True)
    return

def writeSongPlayerTxt():
    global currentSong

    # current song can be null
    o = subprocess.check_output("mpc current", shell=True)
    songAndTitle = o.decode("utf-8")
    if songAndTitle != "":
        songAndTitle = songAndTitle.rstrip()

    i = songAndTitle.find("-") + 2
    currentSong = songAndTitle[i:]

    f = open(currentSongConfig, 'w')
    f.write(currentSong + "\n")
    f.write(str(currentVolume) + "\n")
    f.write(currentPlaylist + "\n")
    f.close()

def initFM():
    printMsg("Initializing FM Radio")
    # Use BCM pin numbering
    GPIO.setmode(GPIO.BCM)
    # Disable warning messages
    GPIO.setwarnings(False)

    # Reset pin on Si4703, and BCM 23 on RPi
    GPIO.setup(RST, GPIO.OUT)
    # SDA or SDIO on Raspberry Pi 3 and same on Si4703
    GPIO.setup(SDA, GPIO.OUT)

    # Temporarily need SDA pin to put SI4703 into 2 wire mode (I2C)
    # The si4703 will not show up in i2cdetect until
    GPIO.output(SDA, GPIO.LOW)
    time.sleep(.1)

    # Transitioning the reset pin from low to high
    # completes putting the Si4703 in 2 wire mode
    GPIO.output(RST, GPIO.LOW)
    time.sleep(.1)
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(.1)

    # Execute a gpio command to restore the SDA pin back to it
    # original i2c SDA line
    #   '-g' causes pin numbers to be BCM
    #   'mode' is the option used to select the mode of the pin
    #   'alt0' is the alternate pin mode code for i2c
    subprocess.check_output(['gpio', '-g', 'mode', str(SDA), 'alt0'])

    readFmRegisters()
    reg[OSCILLATOR] = int(0x8100)
    writeFmRegisters()
    time.sleep(1)

    readFmRegisters()
    reg[POWERCFG] = int(0x4001) #Enable the Radio IC and turn off muted
    writeFmRegisters()
    time.sleep(.1)

    readFmRegisters()
    reg[SYSCONFIG1] |= (1<<12) # Enable RDS
    reg[SYSCONFIG2] &= 0xFFF0; # Clear volume bits 
    reg[SYSCONFIG2] = 0x0000;  # Set volume to lowest
    reg[SYSCONFIG3] = 0x0100;  # Set extended volume range (too loud for me wit$    write_registers()
    return

def initStation():
    global stationList
    global currentPlaylist


    currentPlaylist = "all_stations"

    cmd = "mpc clear" + limitMPCoutput
    subprocess.call(cmd, shell=True)

    # on start up initialize the station list
    stationList = list()

    # open all stations and fill in the stationList data structure
    f = open(allStationsFile, 'r')

    printMsg("Loading stations")
    for line in f:
        line = line.strip()
        if line:
            # line is not blank
            l = line.split(',')
            d = (l[0],l[1],l[2],l[3])
            stationList.append(d)

    f.close()

    readStreamPlayerConfig()

    printMsg("volume = [" + str(currentVolume) + "]")
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)
    if currentStation == "":
        cmd = "mpc play " + limitMPCoutput
        subprocess.call(cmd, shell=True)
    else:
        switchStation(cStation)
    return


def initSong():
    printMsg("Initializing song")
    readACRConfig()

    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

    if playState == "on":
        if currentSong == "":
            cmd = "mpc play " + limitMPCoutput
        else:
            cmd = 'mpc searchplay title "' + currentSong + '"' + limitMPCoutput

        subprocess.call(cmd, shell=True)

    return

# Insert music from my Apple library into mpd and save it as a playlist
def initPlaylist(playlist_name):
    global currentPlaylist

    cmd = "mpc clear" + limitMPCoutput
    subprocess.call(cmd, shell=True)

    printMsg("Loading songs takes a few minutes. Please wait for > prompt")
    for file in os.listdir(directoryMusic):
        if file.endswith(".m4a"):
            dirName = os.path.join(directoryMusic, file)
            fileName = "file://" + dirName
            cmd = 'mpc insert ' + '"' + fileName + '"'
            subprocess.call(cmd, shell=True)

    cmd = "mpc save " + playlist_name
    subprocess.call(cmd, shell=True)

    currentPlaylist = playlist_name
    return

def removePlaylist(p):
    if p == defaultPlaylist:
        printMsg("Cannot remove default playlist: " + defaultPlaylist)
    else:
        cmd = "mpc stop " + limitMPCoutput
        subprocess.call(cmd, shell=True)
        printMsg("Remove playlist " + p)
        cmd = "mpc rm " + p + limitMPCoutput
        subprocess.call(cmd, shell=True)
        cmd = "mpc clear --wait " + limitMPCoutput
        subprocess.call(cmd, shell=True)

        initPlaylist(defaultPlaylist)


##########
printMsg("Starting Alarm Clock Radio")
printMsg("After reboot, mpd loads last playlist. Please wait ...")

try:
    playState = "off"
    exitCondition = "x"

    cmd = 'mpc stop'
    subprocess.call(cmd, shell=True)

    # The Raspberry Pi 3 has two I2C busses and FM Radio uses bus 1
    # Bus 1 uses SDA.1 (BCM pin 2) and SCL.1 (BCM pin 3)
    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    i2c = smbus.SMBus(1)

    initSong()

    updateDate()

    radioGUI.mainloop()

except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt
    printMsg("keyboard exception occurred")

except Exception as ex:
    printMsg("ERROR: an unhandled exception occurred: " + str(ex))

finally:
    printMsg("Alarm Clock Radio terminated")
    writeSongPlayerTxt()
    writeStationPlayerTxt()
    backlight.stop()
    # for FM Radio
    GPIO.output(RST, GPIO.LOW)
    GPIO.cleanup()

    if exitCondition == "x":
        printMsg("... Song still playing")
        fileLog.close()
    elif exitCondition == "o":
        subprocess.call("mpc stop ", shell=True)
        printMsg("... Shutting down raspberry pi")
        fileLog.close()
        subprocess.call("sudo shutdown -h 0", shell=True)
    else:
        subprocess.call("mpc stop ", shell=True)
        fileLog.close()

