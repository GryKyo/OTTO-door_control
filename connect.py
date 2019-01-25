import network
from credentials import SSID, password, static,
gateway, mask, DNS


def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network now...')
        sta_if.active(True)
        sta_if.ifconfig(('static', 'mask', 'gateway', 'DNS'))
        sta_if.connect('SSID', 'password')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
