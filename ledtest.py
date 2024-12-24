import time
import wiringpi
import sys

def blink(_pin):
    wiringpi.digitalWrite(_pin, 1)
    time.sleep(0.5)
    wiringpi.digitalWrite(_pin, 0)
    time.sleep(0.5)

print("start")
pin = 2
wiringpi.wiringPiSetup()
wiringpi.pinMode(pin, 1)

for i in range(0,10):
    blink(pin)

print("Done")
    