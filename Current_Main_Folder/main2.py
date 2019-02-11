# Modules needed to run the script
import os
from machine import *
import time
import credentials
import connect
from umqtt.simple import MQTTClient
import ujson
import ubinascii
import urequests


# some variables which may be called as Globals
lifting = False  # while the door is moving upwards
lowering = False  # while the door is moving downwards
opto_1 = False  # flag set by interrupt on rising or falling value
opto_2 = False  # flag set by interrupt on rising or falling value
door_up = False  # main function must refresh these values "while True"
door_down = False  # main function must refresh these values "while True"
cmd_down = False  # a flag used to see if a "dead-man" MQTT signal is present to lower the door
incoming_msg = "" # empty string until we use it later...
blank_incoming_msg = "" # empty string until we use it later...
timeout = False # a timer used to stop the door if opto fails



# set up some OUTPUT pins
ONBOARD_LED = machine.Pin(22, machine.Pin.OUT)
ONBOARD_LED.value(1)

RLY_UP = machine.Pin(25, machine.Pin.OUT)
RLY_UP.value(1)

RLY_STOP = machine.Pin(33, machine.Pin.OUT)
RLY_STOP.value(1)

RLY_DOWN = machine.Pin(32, machine.Pin.OUT)
RLY_DOWN.value(1)

RLY_BEEPER = machine.Pin(34, machine.Pin.OUT)
RLY_BEEPER.value(1)




# handle interrupt requests from input Pins
def input_callback(p):
    global opto_1
    global opto_2
    if p == FOB_A:
        print("input - Fob A")
        button_A()
    elif p == FOB_B:
        print("input - Fob B")
        button_B()
    elif p == FOB_C:
        print("input - Fob C")
        button_C()
    elif p == FOB_D:
        print("input - Fob D")
        button_D()
    elif p == OPT_1:
        if not OPT_1.value():
            opto_1 = True
            print("opto_1 = True")
        elif OPT_1.value():
            opto_1 = False
            print("opto_1 = False")
    elif p == OPT_2:
        if not OPT_2.value():
            opto_2 = True
            print("opto_2 = True")
        elif OPT_2.value():
            opto_2 = False
            print("opto_2 = False")
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
OPT_1 = machine.Pin(12, machine.Pin.IN)
OPT_1.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
OPT_2 = machine.Pin(14, machine.Pin.IN)
OPT_2.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)
RFID_DIO = machine.Pin(26, machine.Pin.IN)
RFID_DIO.irq(trigger=Pin.IRQ_RISING, handler=input_callback)


# what to do if Button A is pressed on fob
def button_A():
    global lifting
    global lowering
    if lifting:  # button_A stops lifting if already started
        stop_now()
        print("Stopping lifting now by button A")
    elif not lifting:  # DON't if we are fully open
            print("Door ready to lift, Button A, lifting now")
            lifting = True
            lift_now()


# door controls mostly related to BUTTON A on the key fob
# how to stop the door once moving
def stop_now():
    global lifting
    global lowering
    print("Stop command -stop_now function")
    lifting = False
    lowering = False
    entry = time.ticks_ms()
    RLY_STOP.value(0)
    while not RLY_STOP.value():
        if time.ticks_ms() >= entry + 500:
            RLY_STOP.value(1)

# move the door upwards
def lift_now():
    entry = time.ticks_ms()
    RLY_UP.value(0)
    while not RLY_UP.value():
        if time.ticks_ms() >= entry + 500:
            RLY_UP.value(1)

#  what to do if fob BUTTON B is pressed - mostly lowering door
def button_B():
    global lifting
    global lowering
    print("Lower command received")
    entry = time.ticks_ms()
    if lifting:  # Stop first if the door is lifting
        lifting = False  # Stopped lifting
        print("Halting door to change direction")
        RLY_STOP.value(0)
        while RLY_STOP.value():
            if time.ticks_ms() >= entry + 500:
                RLY_STOP.value(1)
    if FOB_B.value():  # These conditions to lower the door
        lowering = True
    elif not FOB_B.value():
        lowering = False


#  what to do if BUTTON C is pressed - mostly stopping evrything
def button_C():
  stop_now()
  lifting = False
  lowering = False
  print("button C funciton called")


#  what to do if fob BUTTON D is pressed - just sounding the beacon
def button_D():
    if FOB_D.value(1):
        RLY_BEEPER.value(0)
    else:
        RLY_BEEPER.value(1)


# run WiFi connect script - credentials are externally stored
connect.do_connect()

#  MQTT server and creds to connect - credentials are externally stored
CLIENT_ID = ubinascii.hexlify(machine.unique_id()) # CLIENT_ID is unique & local



# the callback to handle MQTT messages
def sub_cb(topic, msg):
    print((topic, msg))
    global cmd_up
    global cmd_down
    global incoming_msg
    incoming_msg = str(msg)
    if topic == b"otto/cmd":
        if msg == b"up":
          cmd_up = True
          button_A()
        if msg == b"LowerButtonDown":  # These conditions to lower the door
            cmd_down = True
        if msg == b"LowerButtonUp":  # These conditions to lower the door
            cmd_down = False
    elif topic == b"otto/rfid":
        #print((topic, msg))
        raw = str(msg)
        parsed_msg = ujson.loads(raw) # convert JSON to a type DICT
        print("Parsed JSON : ", parsed_msg)
        log_data = parsed_msg["username"]  # get some data from the msg
        response = urequests.get(credentials.google_string, log_data)
        access = parsed_msg["isKnown"]
        print("This tag is known, it is ", access)
        if access == "true":
            print("...and access is granted")
            button_A()
        elif access == "false":
            print("...and access is denied")


  #  Most of the program is here
def main(server=credentials.SERVER, port=credentials.PORT, user=credentials.USER, password=credentials.PASSWORD):
    client = MQTTClient(CLIENT_ID, server, port, user, password)
    client.set_callback(sub_cb)
    client.connect()
    print("Connected to MQTT broker ", SERVER)
    client.subscribe("otto/cmd")
    global lifting
    global door_down
    global incoming_msg
    global blank_incoming_msg
    last_door_down = 1
    last_lifting = 0
    try:
      while True:
        if opto_1 and not opto_2:
          door_up = True
        else:
          door_up = False
        if not opto_1 and not opto_2:
          door_down = True
        else:
            door_down = False
        if lifting | lowering:
            RLY_BEEPER.value(0)
        else:
            RLY_BEEPER.value(1)
        if lifting != last_lifting:
          if lifting:
            entry = time.ticks_ms()
        if lifting and (time.ticks_ms() >= entry + 7500):
          timeout = True
          lifting = False
          print("timeout!")
        if incoming_msg != blank_incoming_msg:
          client.publish(b"otto/stat", b"Got a new message")
        last_lifting = lifting
        last_door_down = door_down
        incoming_msg = ""
        blank_incoming_msg = ""
        client.check_msg()


    except KeyboardInterrupt:
      print("Graceful exit by keyboard interrupt")
      client.publish(b"otto/stat", b"Graceful exit by keyboard interrupt")
    finally:
      print("Code crashed, idle now")
      client.publish(b"otto/stat", b"Code stopped, ESP32 idle now")

#  run the main module
if __name__ == '__main__':
    main()
