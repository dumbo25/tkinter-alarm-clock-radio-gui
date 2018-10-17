#!/usr/bin/env python3

#########################
#
# acr.py is a python3 script using tkinter, mpd and mpc and crontab
# to create an alarm clock radio
#
# Start the script running using:
#    python3 acr.py
#
# acr.py was tested on a Raspberry Pi 3 model B+ running raspbian
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
#    On Raspberry Pi
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
#       Playlists are stored here:
#          /var/lib/mpd/playlists
#
#       Songs are stored here:
#          /home/pi/Music
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
#   Use the first three letters of the particular day or month (case doesn't matter)
#   A field may be an asterisk (*), which I understand to be ignore
#
#   Add slash /n to repeat every n months/days/hours/minutes
#   Use comma to specify multiples 0 5 * * 1,2,3,4,5 to run alarm every business day
#
# Three question (???) marks indicate features requiring more work
#
# To Do List:
#    ??? HDMI mirroring may be causing the screen size to be messed up
#
# Notes:
#    If music file name contains a backquote, you will get error message:
#       EOF in backquote substitution
#
#########################

############
import time
import datetime
import os
import sys
import subprocess
import tkinter as tk
from crontab import CronTab
import RPi.GPIO as GPIO

#########################
# Global Variables
fileLog = open('/home/pi/radio/acr.log', 'w+')

defaultVolume = 60
currentVolume = defaultVolume

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

# Instead of starting with the first song every time, remember
# last song played or get current song playing and start playing
# it
currentSong = ""

# On mpc commands like play, prev and next, mpc outputs a line
# similar to:
#
#    volume: n/a repeat: off random: off single: off consume: off
#
# adding the following to any mpc command suppresses that output
limitMPCoutput = " | grep \"[-,'[']\""


# Global tkinter GUI variables

# radioGUI is the main tkinter window
# radioGUI has 6 columns and 6 rows
radioGUI = tk.Tk()

# since the alarm clock will be used in a bedroom at night. the
# background and color scheme should be easily readable at night
# while not being too bright
radioGUI.configure(background='black')

# make radioGUI use full screen
radioGUI.overrideredirect(True)
radioGUI.geometry("{0}x{1}+0+0".format(radioGUI.winfo_screenwidth(), radioGUI.winfo_screenheight()))

# Global tkinter widget variables
dateRow = 0
dateText = tk.StringVar()
dateLabel = tk.Label(radioGUI, font=('arial', 30, 'bold'), fg='red', bg='black', textvariable=dateText)
dateLabel.grid(row=dateRow, columnspan=6)

timeRow = 1
timeText = tk.StringVar()
timeLabel = tk.Label(radioGUI, font=('digital-7', 120), fg='red', bg='black', textvariable=timeText, anchor='n')
timeLabel.grid(row=timeRow, columnspan=6)

alarmRow = 2
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

# 17 toggles backlight on and off
GPIO.add_event_detect(17, GPIO.FALLING, callback=toggleBacklight, bouncetime=200)

# event handler to reboot the Raspberry Pi
def reboot(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo reboot"
        subprocess.call(cmd, shell=True)

# 23 reboots the Raspberry Pi
GPIO.add_event_detect(23, GPIO.FALLING, callback=reboot, bouncetime=200)

# event handler to shutdown the Raspberry Pi
def shutdown(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo shutdown -h 0"
        subprocess.call(cmd, shell=True)

# 27 shuts down the Raspberry Pi
GPIO.add_event_detect(27, GPIO.FALLING, callback=shutdown, bouncetime=200)

# event handler to exit the script
def exitButtonPress(channel):
    global radioGUI

    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)

    radioGUI.quit()

# 22 exits this script
GPIO.add_event_detect(22, GPIO.FALLING, callback=exitButtonPress, bouncetime=200)

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
    timeText.set(tts+'\n')

    # update every 2 seconds, should be accurate enough
    radioGUI.after(2000, updateDate)

# Set Alarm Row
# skip first column
setAlarmRow = 4

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
        cmd = "mpc stop " + limitMPCoutput
        subprocess.call(cmd, shell=True)
    else:
        # change from off to on
        playState = "on"
        playStopButton.configure(image=stopImage)
        cmd = "mpc play" + limitMPCoutput
        subprocess.call(cmd, shell=True)

playStopButton = tk.Button(radioGUI, command=playStopPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
playStopButton.configure(image=playImage)
playStopButton.grid(row=controlRow, column=1)

def backPress():
     cmd = "mpc prev " + limitMPCoutput
     subprocess.call(cmd, shell=True)

backImage = tk.PhotoImage(file='/home/pi/radio/images/back.gif')
backButton = tk.Button(radioGUI, image=backImage, command=backPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
backButton.grid(row=controlRow, column=2)

def nextPress():
     cmd = "mpc next " + limitMPCoutput
     subprocess.call(cmd, shell=True)

nextImage = tk.PhotoImage(file='/home/pi/radio/images/next.gif')
nextButton = tk.Button(radioGUI, image=nextImage, command=nextPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
nextButton.grid(row=controlRow, column=3)

def volumeUpPress():
    global currentVolume

    # volume up
    currentVolume +=5
    if currentVolume > 100:
        currentVolume = 100
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

volumeUpImage = tk.PhotoImage(file='/home/pi/radio/images/volumeup.gif')
volumeUpButton = tk.Button(radioGUI, image=volumeUpImage, command=volumeUpPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0).grid(row=controlRow, column=4)

def volumeDownPress():
    global currentVolume

    # volume down
    currentVolume -=5
    if currentVolume < 0:
        currentVolume = 0
    cmd = "amixer set Digital " + str(currentVolume) + "%"
    subprocess.call(cmd, shell=True)

volumeDownImage = tk.PhotoImage(file='/home/pi/radio/images/volumedown.gif')
volumeDownButton = tk.Button(radioGUI, image=volumeDownImage, command=volumeDownPress, bg='black', borderwidth=0, relief="flat", highlightcolor="black", highlightbackground="black", highlightthickness=0)
volumeDownButton.grid(row=controlRow, column=5)

############
#### above is gui.py code
############

#########################
# Log messages should be time stamped
def timeStamp():
    t = time.time()
    s = datetime.datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S - ')
    return s

# Write messages in a standard format
def printMsg(s):
    fileLog.write(timeStamp() + s + "\n")

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

def init():
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

    init()

    exitCondition = "x"

    updateDate()

    radioGUI.mainloop()

except KeyboardInterrupt: # trap a CTRL+C keyboard interrupt
    printMsg("keyboard exception occurred")

except Exception as ex:
    printMsg("ERROR: an unhandled exception occurred: " + str(ex))

finally:
    printMsg("Alarm Clock Radio terminated")
    writeSongPlayerTxt()
    backlight.stop()
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

