#   This script is used to control the screen power state using a button connected to GPIO pins on a Raspberry Pi.
import RPi.GPIO as GPIO
import time
import os

# buttons.py
# Set up the GPIO pin for the button and screen control
# Ensure the raspi-gpio utility is installed and configured
os.system('raspi-gpio set 19 ip')
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(18, GPIO.OUT)


# Function to turn on the screen by setting GPIO pin 19 to output and turning on GPIO pin 18
def turnOnScreen():
    os.system('raspi-gpio set 19 op a5')
    GPIO.output(18, GPIO.HIGH)


# Function to turn off the screen by setting GPIO pin 19 to input and turning off GPIO pin 18
def turnOffScreen():
    os.system('raspi-gpio set 19 ip')
    GPIO.output(18, GPIO.LOW)


# Initialize the screen state
turnOffScreen()
screen_on = False

# Main loop to check the button state and control the screen
while (True):
    # If you are having and issue with the button doing the opposite of what you want
    # IE Turns on when it should be off, change this line to:
    # input = not GPIO.input(26)
    input = GPIO.input(26)
    if input != screen_on:
        screen_on = input
        if screen_on:
            turnOnScreen()
        else:
            turnOffScreen()
    time.sleep(0.3)