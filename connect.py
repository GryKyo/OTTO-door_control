import network
import credentials


def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network now...')
        sta_if.active(True)
        sta_if.ifconfig((credentials.static, credentials.mask,
                         credentials.gateway, credentials.DNS))
        sta_if.connect(credentials.SSID, credentials.password)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
