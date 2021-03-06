# Modules needed to run the script
import os
import machine
from machine import Pin
import time
import credentials
import connect
from umqtt.simple import MQTTClient
import ujson
import ubinascii
import urequests


# some variables which may be called as Globals
lifting = False  # while the door is moving upwards
last_lifting = False  #  temp store lifting state leaving loop
lowering = False  # while the door is moving downwards
last_lowering = False #  temp store lowering state leaving loop
opto_1 = False  # flag set by interrupt on rising or falling value
opto_2 = False  # flag set by interrupt on rising or falling value
door_up = False  # main function must refresh these values "while True"
last_door_up = False # temp store open/not open state leaving loop
door_down = False  # main function must refresh these values "while True"
last_door_down = False # temp store closed/not closed state leaving loop
cmd_down = False  # a flag used to see if a "dead-man" MQTT signal is present to lower the door
cmd_down = False  # a flag used to see if a "dead-man" MQTT signal is present to lower the door
incoming_msg = "" # empty string until we use it later...
blank_incoming_msg = "" # empty string until we use it later...
timeout = False # a timer used to stop the door if opto fails
response = ""


# set up some OUTPUT pins
ONBOARD_LED = machine.Pin(22, machine.Pin.OUT)
ONBOARD_LED.value(1)
RLY_UP = machine.Pin(25, machine.Pin.OUT)
RLY_UP.value(1)
RLY_STOP = machine.Pin(33, machine.Pin.OUT)
RLY_STOP.value(1)
RLY_DOWN = machine.Pin(32, machine.Pin.OUT)
RLY_DOWN.value(1)
RLY_BEEPER = machine.Pin(26, machine.Pin.OUT)
RLY_BEEPER.value(1)


# handle interrupt requests from the input Pins
def input_callback(p):
    global opto_1
    global opto_2
    if p == FOB_A:
        button_A()
    elif p == FOB_B:
        button_B()
    elif p == FOB_C:
         button_C()
    elif p == FOB_D:
        button_D()
    elif p == RFID_DIO:
        button_A()
    elif p == OPT_1:
        if OPT_1.value():
            opto_1 = True
         elif not OPT_1.value():
            opto_1 = False
    elif p == OPT_2:
        if OPT_2.value():
            opto_2 = True
        elif not OPT_2.value():
            opto_2 = False
    elif p == RFID_DIO.value():
        button_A()

# set up all INPUT pins and IRQ triggers to catch inputs
FOB_A = machine.Pin(16, machine.Pin.IN)
FOB_A.irq(trigger=Pin.IRQ_RISING, handler=input_callback)
FOB_B = machine.Pin(4, machine.Pin.IN)
FOB_B.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
FOB_C = machine.Pin(0, machine.Pin.IN)
FOB_C.irq(trigger=Pin.IRQ_RISING, handler=input_callback)
FOB_D = machine.Pin(2, machine.Pin.IN)
FOB_D.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
OPT_1 = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
OPT_1.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
OPT_2 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
OPT_2.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
RFID_DIO = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
RFID_DIO.irq(trigger=Pin.IRQ_RISING, handler=input_callback)


# what to do if Button A is pressed on fob
def button_A():
    global lifting
    global lowering
    if lifting:  # button_A stops lifting if already started
        stop_now()
    elif not lifting and not door_up:  # DON't if we are fully open
            lifting = True
            lift_now()

#  what to do if fob BUTTON B is pressed - mostly lowering door
def button_B():
    global lifting
    global lowering
    entry = time.ticks_ms()
    if lifting:  # Stop first if the door is lifting
        lifting = False  # Stopped lifting
        RLY_STOP.value(0)
        while not RLY_STOP.value():
            if time.ticks_ms() >= entry + 500:
                RLY_STOP.value(1)
    if FOB_B.value():  # These conditions to lower the door
        lowering = True
    elif not FOB_B.value():
        lowering = False

#  what to do if BUTTON C is pressed - mostly stopping evrything
def button_C():
  global lifting
  global lowering
  stop_now()
  lifting = False
  lowering = False

#  what to do if fob BUTTON D is pressed - just sounding the beacon
def button_D():
    if FOB_D.value(1):
        RLY_BEEPER.value(0)
    else:
        RLY_BEEPER.value(1)

# door controls mostly related to BUTTON A on the key fob
# how to stop the door once moving
def stop_now():
    global lifting
    global lowering
    client.publish(b"otto/stat", b"stop")
    lifting = False
    lowering = False
    entry = time.ticks_ms()
    RLY_STOP.value(0)
    while not RLY_STOP.value():
        if time.ticks_ms() >= entry + 500:
            RLY_STOP.value(1)

# move the door upwards
def lift_now():
    if not door_up:
      entry = time.ticks_ms()
      RLY_UP.value(0)
      while not RLY_UP.value():
          if time.ticks_ms() >= entry + 500:
              RLY_UP.value(1)

# Ready to hit the internet, find MQTT broker and do stuff

connect.do_connect() # run WiFi connect script
# credentials are externally stored


#  MQTT unique ID and creds to connect - credentials are externally stored
CLIENT_ID = ubinascii.hexlify(machine.unique_id()) # CLIENT_ID is unique & local


# a callback function to handle inbound MQTT messages
def sub_cb(topic, msg):
    print((topic, msg))
    global cmd_up
    global cmd_down
    if topic == b"otto/cmd": # this topic receives action commands
        if msg == b"up":
          button_A()
        if msg == b"stop":
          stop_now()
        if msg == b"LowerButtonDown":  # like a "key down" stroke
            cmd_down = True
            print("cmd_down is : ", cmd_down)
            client.publish(b"otto/stat", "lowering") # broadcast that we are lowering the door
        if msg == b"LowerButtonUp":  # like a "key up" stroke
            cmd_down = False
            stop_now()
            print("cmd_down is : ", cmd_down)
    elif topic == b"otto/rfid": # This topic receives a json object from the RFID
        parsed_msg = ujson.loads(msg) # convert JSON to a type DICT
        print("Parsed JSON : ", parsed_msg)
        if parsed_msg["type"] == "heartbeat": # ignore this, don't crash!
          return None
        if parsed_msg["type"] == "boot": # ignore this, don't crash!
          return None
        access = parsed_msg["isKnown"]  #  this is the key for access/no access
        print("This tag is known, it is ", parsed_msg["username"])
        if access == "true":
            print("...and access is granted")
            button_A()  #  open or stop lifting the door using RFID & MQTT
        elif access == "false":
            print("...and access is denied")
        log_data = parsed_msg["username"]  # get some data from the msg
        response = urequests.get(credentials.google_string + str(log_data)) # Post to log file on Google Drive
        response.close()

client = MQTTClient(CLIENT_ID, credentials.SERVER, credentials.PORT, credentials.USER, credentials.PASSWORD)
client.set_callback(sub_cb)
client.connect()
print("Connected to MQTT broker ", credentials.SERVER)
client.subscribe(b"otto/#")
client.publish(b"otto/stat", b"Client is subscribed to topic otto/stat")

#  Looping forever now
try:
  while True:
    response  = ""
    if not opto_1 and opto_2:  #  This is the open/closed logic
      door_up = True
    else:
      door_up = False
    if opto_1 and opto_2:
      door_down = True
    else:
        door_down = False
    if cmd_down or lowering:   #  This controls the lowering signal - "deadman so must be in loop"
      if not door_down:
          RLY_DOWN.value(0)
    else:
        RLY_DOWN.value(1)
    if lifting or lowering:
        RLY_BEEPER.value(0)
    else:
        RLY_BEEPER.value(1)
    if lifting != last_lifting: # detect state change to broadcast the change
      if lifting:
        start_timing = time.ticks_ms()
        client.publish(b"otto/stat", b"lifting")
    if lowering != last_lowering: # detect state change to broadcast the change
      if lowering:
        client.publish(b"otto/stat", b"lowering")
    if lifting and (time.ticks_ms() >= start_timing + 7500):
      stop_now()
      print("timeout!")
    if door_down != last_door_down:
        if door_down:  # the door is closed, stop closing!
            stop_now()
    if door_up != last_door_up:
        if door_up:   #  the door is fully up, stop lifting!
            stop_now()
    last_lifting = lifting
    last_lowering = lowering
    last_door_down = door_down
    last_door_up = door_up
    client.check_msg()
except KeyboardInterrupt:
  client.publish(b"otto/stat", b" exit by keyboard interrupt")
finally:
  client.publish(b"otto/stat", b"Code stopped, ESP32 idle now")


