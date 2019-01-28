import os
import machine
from machine import Pin
import time
import credentials
import connect
from umqtt.simple import MQTTClient


# some variables which may be called as Globals
lifting = False  # while the door is moving upwards
lowering = False  # while the door is moving downwards
opto_1 = False  # flag set by interrupt on rising or falling value
opto_2 = False  # flag set by interrupt on rising or falling value
door_up = False  # main function must refresh these values "while True"
door_down = False  # main function must refresh these values "while True"
cmd_down = False  # a flag used to see if a "dead-man" MQTT signal is present to lower the door

# set up some OUTPUT pins
ONBOARD_LED = machine.Pin(22, machine.Pin.OUT)
ONBOARD_LED.value(1)
RLY_UP = machine.Pin(19, machine.Pin.OUT)
RLY_UP.value(0)
RLY_STOP = machine.Pin(23, machine.Pin.OUT)
RLY_STOP.value(0)
RLY_DOWN = machine.Pin(18, machine.Pin.OUT)

RLY_DOWN.value(0)
AUDIO_1 = machine.Pin(5, machine.Pin.OUT)
AUDIO_2 = machine.Pin(17, machine.Pin.OUT)

# handle interrupt requests from input Pins


def input_callback(p):
    global opto_1
    global opto_2
    if p == FOB_A:
        button_A()
    elif p == FOB_B:
        button_B()
    elif p == FOB_C:
        pass
    elif p == FOB_D:
        pass
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


# set up some INPUT pins and IRQ triggers to catch inputs
FOB_A = machine.Pin(34, machine.Pin.IN)
FOB_A.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

FOB_B = machine.Pin(35, machine.Pin.IN)
FOB_B.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)

FOB_C = machine.Pin(32, machine.Pin.IN)
FOB_A.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

FOB_D = machine.Pin(33, machine.Pin.IN)
FOB_D.irq(trigger=Pin.IRQ_RISING, handler=input_callback)

OPT_1 = machine.Pin(25, machine.Pin.IN)
OPT_1.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)

OPT_2 = machine.Pin(26, machine.Pin.IN)
OPT_2.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=input_callback)

# what to do if Button A is pressed on fob


def button_A():
    global lifting
    global lowering
    if lifting:  # button_A stops lifting if already started
        lifting = False
        stop_now()
    if not door_up:  # DON't if we are fully open
        if not lifting:  # okay to lift the door...
            lifting = True
            lift_now()


def stop_now():
    entry = time.ticks_ms()
    RLY_STOP.value(1)
    while RLY_STOP.value():
        if time.ticks_ms() >= entry + 500:
            RLY_STOP.value(0)


def lift_now():
    entry = time.ticks_ms()
    RLY_UP.value(1)
    while RLY_UP.value():
        if time.ticks_ms() >= entry + 500:
            RLY_UP.value(0)


def button_B():
    global lifting
    global lowering
    entry = time.ticks_ms()
    while lifting:  # Stop first if the door is lifting
        lifting = False  # Stopped lifting
        RLY_STOP.value(1)
        while RLY_STOP.value():
            if time.ticks_ms() >= entry + 500:
                RLY_STOP.value(0)
    while FOB_B.value() | cmd_down:
        lowering = True
        RLY_DOWN.value(1)
    while not FOB_B.value() | cmd_down:
        lowering = False
        RLY_DOWN.value(0)


# run WiFi connect script
connect.do_connect()

#  MQTT server and creds to connect
SERVER = "m20.cloudmqtt.com"
USER = "XXXXXX"
PASSWORD = "XXXXXX"
PORT = "XXXXX"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())


def sub_cb(topic, msg):  # the callback to handle MQTT messages
    print((topic, msg))
    global cmd_up
    if topic == b"otto/cmd":
        if msg == b"up"
        cmd_up = True

#  Most of the program is here


def main():
    client = MQTTClient(CLIENT_ID)
    client.connect(host=SERVER, user=USER, password=PASSWORD, port=PORT)
    print("Connected to MQTT broker ", SERVER)
    client.set_callback(sub_cb)
    client.subscribe("otto/#")
    global lifting
    global door_down
    last_door_down = 1
    last_lifting = 0
    try:
        while True:
            if opto_2 and not opto_1:
                door_up = True
            else:
                door_up = False
            if opto_2 and opto_1:
                door_down = True
            else:
                door_down = False
            if lifting != last_lifting:
                if lifting:
                entry = time.ticks_ms()
                   if time.ticks_ms() >= entry + 10000:
                        timeout = True
                    if door_up | timeout:
                        lifting = False
                        timeout = False
                        stop_now()
            if door_down != last_door_down:
                if door_down:
                    stop_now()
            last_lifting = lifting
            last_door_down = door_down
            client.check_msg()
    except KeyboardInterrupt:

        print("Graceful exit by keyboard interrupt")

    finally:
        print("Code stopped, idle now")


if __name__ == '__main__':
    main()
