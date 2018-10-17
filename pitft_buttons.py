#!/usr/bin/env python3

#########################
#
# PiTFT tactile buttons tested on Raspberry Pi 3 running raspbian
# with a 2.8 inch capacitive touch screen
#
# run using:
#
#    $ python3 buttons.py
#
# This script requires the following:
#
#    Raspbery Pi 3 B+ running raspbian
#    HiFiBerry AMP 2
#
# Original code from:
#     Author: chow
#     https://pumpingstationone.org/2016/07/configuring-pi-3-with-a-tft-touchscreen-and-gpio-buttons/
#
# There are four tactile buttons. They can be used for
# anything and in any order. Here is what I chose:
#    #17 toggles backlight on and off
#    #22 exits acr.py
#    #23 reboots the Raspberry Pi
#    #27 shuts down the Raspberry Pi
#
# A common use of the tactile pins is to control the
# backlight. Normally, pin 12 (GPIO 18) is used for
# backlight control, but the HiFiBerry AMP 2 uses GPIO
# 18. To avoid any issues, pin 32 (GPIO 12) on the
# HiFiBerry AMP 2 connects to pin 12 (GPIO 18) on
# the PiTFT.
#
#    12  controls backlight
#
# Three question (???) marks indicate features requiring more work
#
# To Do List:
#    ??? need to write messages to acr.log to show
#        this script is running or if it has exited
#    ??? run this as a service
#
#########################

############
import subprocess
import time
import RPi.GPIO as GPIO

# BCM tactile buttons on 2.8 capacitive touch PiTFT
channel_list = [17, 22, 23, 27]
backlightOn = True

# event handler to toggle the TFT backlight
def toggleBacklight(channel):
    global backlightOn

    if backlightOn:
        backlightOn = False
        backlight.start(0)
    else:
        backlightOn = True
        backlight.start(100)

# event handler to reboot the Raspberry Pi
def reboot(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo reboot"
        subprocess.call(cmd, shell=True)

# event handler to shutdown the Raspberry Pi
def shutdown(channel):
    startTime = time.time()
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.02)
    if (time.time() - startTime) > 2:
        cmd = "sudo shutdown -h 0"
        subprocess.call(cmd, shell=True)

# set GPIO mode
GPIO.setmode(GPIO.BCM)

# initialize GPIO pins
GPIO.setup(channel_list, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# setup backlight GPIO
GPIO.setup(12, GPIO.OUT)
backlight = GPIO.PWM(12, 1000)
backlight.start(100)

# 17 toggles backlight on and off
GPIO.add_event_detect(17, GPIO.FALLING, callback=toggleBacklight, bouncetime=200)

# 23 reboots the Raspberry Pi
GPIO.add_event_detect(23, GPIO.FALLING, callback=reboot, bouncetime=200)

# 27 shuts down the Raspberry Pi
GPIO.add_event_detect(27, GPIO.FALLING, callback=shutdown, bouncetime=200)

try:
    # 22 exits this script, but should kill acr.py: ps -aux | grep acr.py... kill
    GPIO.wait_for_edge(22, GPIO.FALLING)

except:
    pass

# exit gracefully
backlight.stop()
GPIO.cleanup()
