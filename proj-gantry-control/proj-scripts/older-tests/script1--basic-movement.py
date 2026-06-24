from machine import Pin
import time

EN   = Pin(13, Pin.OUT)
DIR  = Pin(14, Pin.OUT)
STEP = Pin(27, Pin.OUT)

EN.value(0)
DIR.value(0)

for i in range(6000):
    STEP.value(1)
    time.sleep_ms(2)
    STEP.value(0)
    time.sleep_ms(2)

EN.value(1)

