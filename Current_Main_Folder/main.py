



import os
import machine
from machine import Pin
import time
import credentials
import connect
from umqtt.simple import MQTTClient
import ubinascii


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
#ONBOARD_LED = machine.Pin(22, machine.Pin.OUT)

#ONBOARD_LED.value(1)

RLY_UP = machine.Pin(22, machine.Pin.OUT)

RLY_UP.value(1)

RLY_STOP = machine.Pin(32, machine.Pin.OUT)

RLY_STOP.value(1)

RLY_DOWN = machine.Pin(21, machine.Pin.OUT)

RLY_DOWN.value(1)

RLY_BEEPER = machine.Pin(33, machine.Pin.OUT)

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
        pass
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

# set up some INPUT pins and IRQ triggers to catch inputs
FOB_A = machine.Pin(16, machine.Pin.IN)

FOB_A.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

FOB_B = machine.Pin(4, machine.Pin.IN)

FOB_B.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)

FOB_C = machine.Pin(0, machine.Pin.IN)

FOB_C.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

FOB_D = machine.Pin(2, machine.Pin.IN)

FOB_D.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

OPT_1 = machine.Pin(12, machine.Pin.IN)

OPT_1.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)

OPT_2 = machine.Pin(13, machine.Pin.IN)

OPT_2.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)


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

    if FOB_B.value() | cmd_down:
        lowering = True
        RLY_DOWN.value(0)
    elif not FOB_B.value():
        lowering = False
        RLY_DOWN.value(1)
    elif not cmd_down:
        lowering = False
        RLY_DOWN.value(1)

def button_C():
  stop_now()
  lifting = False
  lowering = False
  print("button C funciton called")

# run WiFi connect script
connect.do_connect()

#  MQTT server and creds to connect
SERVER = "m20.cloudmqtt.com"
USER = "rmfhlxgf"
PASSWORD = "4e8hGCapvTQv"
PORT = "14928"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())



# the callback to handle MQTT messages
def sub_cb(topic, msg):
    print((topic, msg))
    global cmd_up
    global incoming_msg
    incoming_msg = str(msg)
    if topic == b"otto/cmd":
        if msg == b"up":
          cmd_up = True
          button_A()


  #  Most of the program is here
def main(server=SERVER, port=PORT, user=USER, password=PASSWORD):
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
        if lifting != last_lifting:
          if lifting:
            entry = time.ticks_ms()
            if time.ticks_ms() >= entry + 10000:
              timeout = True
              print("timeout!")
              if door_up | timeout:
                lifting = False
                timeout = False
                stop_now()
            if door_down != last_door_down:
              if door_down:
                stop_now()
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
