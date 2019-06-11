from umqtt.simple import MQTTClient
from machine import Pin
import ubinascii
import machine, neopixel
import micropython
import connect
import os
import time


# Let's try to connect to the intetnet
connect.do_connect()

# ESP8266 ESP-12 modules have blue, active-low LED on GPIO2, replace
# with something else if needed.
led = Pin(2, Pin.OUT, value=1)

num = 12 # Full number of neopixels
neo = neopixel.NeoPixel(machine.Pin(4), num)

# Default MQTT server to connect to
SERVER = "192.168.2.224"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())
TOPIC = b"hallway"

s = 1 # number of flashes
delay = 250 # flash interval
red = (255, 0, 0) #colour tuple
green = (0, 128, 0) #colour tuple
blue = (0, 0, 128) #colour tuple
state = 0 # initial state

def flash(colour, s, delay): # function to flash neopixels any way we like
  for i in range (s):
      neo.fill((colour))
      neo.write()
      time.sleep_ms(delay)
      neo.fill((0, 0, 0))
      neo.write()
      time.sleep_ms(delay)

def sub_cb(topic, msg):
    global state
    print((topic, msg))
    if msg == b"1":
        led.value(0)
        state = 1
        flash(red, 10, 150)
    elif msg == b"0":
        led.value(1)
        state = 0
        flash(green, 2, 100)
    elif msg == b"toggle":
        # LED is inversed, so setting it to current state
        # value will make it toggle
        led.value(state)
        state = 1 - state


def main(server=SERVER):
    c = MQTTClient(CLIENT_ID, server)
    # Subscribed messages will be delivered to this callback
    c.set_callback(sub_cb)
    c.connect()
    c.subscribe(TOPIC)
    print("Connected to %s, subscribed to %s topic" % (server, TOPIC))
    flash(blue, 3, 100)

    try:
        while 1:
            #micropython.mem_info()
            c.wait_msg()
    finally:
        c.disconnect()

if __name__ == "__main__":
    main()
