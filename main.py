from machine import Pin
from time import sleep

led = Pin(2, Pin.OUT)
state = 0
while True:
    led.value(not led.value())
    if(led.value() == 1):
        print("Led is On")
    else:
        print("Led is Off")
    
    sleep(0.5)
