#!/usr/bin/env python3

import traceback
# from eth_account.account import Account
# from eth_account.messages import encode_defunct, defunct_hash_message
import logging
import os
import struct
import array
from enum import Enum

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import socket

from gatt.ble import (
    Advertisement,
    Characteristic,
    Service,
    Application,
    find_adapter,
    Descriptor,
)
import datetime
import json
from gatt.eth import sign_message
from gatt.utils import *
import subprocess
from gatt.agent import Agent
from gatt.autoconnect import listDevices
# Mainloop
MainLoop = None
try:
    from gi.repository import GLib

    MainLoop = GLib.MainLoop
except ImportError:
    import gobject as GObject

    MainLoop = GObject.MainLoop


# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
filelogHandler = logging.FileHandler("logs.log")
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logHandler.setFormatter(formatter)
filelogHandler.setFormatter(formatter)
logger.addHandler(filelogHandler)
logger.addHandler(logHandler)

# Service
mainloop = None

# Constants
BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"


bus = None

# Callbacks


def register_app_cb():
    logger.info("GATT application registered")


def register_app_error_cb(error):
    logger.critical("Failed to register application: " + str(error))
    mainloop.quit()


def register_ad_cb():
    logger.info("Advertisement registered")


def register_ad_error_cb(error):
    logger.critical("Failed to register advertisement: " + str(error))
    mainloop.quit()


# Classes

class AutoPiS1Service(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """

    SVC_UUID = '58de7278-4723-48a9-8af5-c524617103bd'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SVC_UUID, True)
        self.add_characteristic(SignedToken(bus, 0, self))
        IS_PAIRED, OWNER_ETH_ADDRESS, COMMUNICATION_PUBLIC_KEY = getEnvVars()
        if(IS_PAIRED):
            self.isPaired = True
            self.comm_key = COMMUNICATION_PUBLIC_KEY
            self.add_characteristic(CPUTemp(bus, 1, self))
        else:
            self.isPaired = False
            self.comm_key = None


def dump_json(data):
    return json.dumps(data, separators=(',', ':'))


def dev_disconnect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path),
                         "org.bluez.Device1")

    dev.Disconnect()


def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path),
                         "org.bluez.Device1")

    dev.Connect()


class SignedToken(Characteristic):
    uuid = 'ce878653-8c44-4326-84e5-3be6c0fa341f'
    description = b'signed token'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, [
                "read", "write"], service,
        )

        self.value = [0xFF]
        self.add_descriptor(
            CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):

        token = {"timestamp": datetime.datetime.now().isoformat()}
        signature = sign_message(dump_json(token))
        #signature = dump_json(token)
        signedToken = dump_json({"token": token, "signature": signature})
        logger.info(signedToken)
        return str.encode(signedToken)

    def WriteValue(self, value, options):
        logger.info(options)
        logger.info(options["device"])
        dev_disconnect(options["device"])
        logger.info("Test Write: " + repr(value))
        cmd = bytes(value).decode("utf-8")
        logger.info("Decoded: " + cmd)
        #os.system('autopi audio.speak "' + cmd + '"')

        return None


class CPUTemp(Characteristic):
    uuid = 'ce878654-8c44-4326-84e5-3be6c0fa341f'
    description = b'CPU temp'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, [
                "read", "write"], service,
        )
        IS_PAIRED, OWNER_ETH_ADDRESS, COMMUNICATION_PUBLIC_KEY = getEnvVars()
        self.isPaired = IS_PAIRED
        self.comm_key = COMMUNICATION_PUBLIC_KEY
        self.value = ""

    def verify_token(self, data):
        return True
        # token_json = data["data"]["token"]
        # token = dump_json(token_json)
        # signature = data["data"]["signature"]
        # msg_hash = defunct_hash_message(text=token)
        # hex_sig = int(signature, 16)
        # address = Account.recoverHash(msg_hash, signature=hex_sig)
        # logger.info("Expected, recovered: %s, %s" % (self.comm_key, address))
        # if(address == self.comm_key):
        #     return True
        # else:
        #     return False

    def ReadValue(self, options):
        return str.encode(self.value)

    def WriteValue(self, value, options):
        try:
            val_str = bytes(value).decode("utf-8")
            print(options, val_str)
            data = json.loads(val_str)
            if(self.verify_token(data)):
                self.value = subprocess.check_output(
                    ["vcgencmd", "measure_temp"]).decode("utf-8").split("\n")[0]
            else:
                self.value = "error"
                print(options["device"])
                dev_disconnect(options["device"])
        except:
            traceback.print_exc()


class AutoPiAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_local_name(socket.gethostname())
        self.add_service_uuid(AutoPiS1Service.SVC_UUID)


def extract_objects(object_list):
    list = ""
    for object in object_list:
        val = str(object)
        list = list + val[val.rfind("/") + 1:] + " "
    return list


def extract_uuids(uuid_list):
    list = ""
    for uuid in uuid_list:
        if (uuid.endswith("-0000-1000-8000-00805f9b34fb")):
            if (uuid.startswith("0000")):
                val = "0x" + uuid[4:8]
            else:
                val = "0x" + uuid[0:8]
        else:
            val = str(uuid)
        list = list + val + " "
    return list


def main():
    global mainloop
    global bus

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    IS_PAIRED, OWNER_ETH_ADDRESS, COMMUNICATION_PUBLIC_KEY = getEnvVars()
    if IS_PAIRED:
        logger.info("Paired, %s, %s" %
                    (OWNER_ETH_ADDRESS, COMMUNICATION_PUBLIC_KEY))
    else:
        logger.info("Not Paired")

    # get the system bus
    bus = dbus.SystemBus()

    # get the ble controller
    adapter = find_adapter(bus)

    if not adapter:
        logger.critical("GattManager1 interface not found")
        return

    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter)

    adapter_props = dbus.Interface(
        adapter_obj, "org.freedesktop.DBus.Properties")

    # powered and pairable property on the controller to on
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
    adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(0))
    adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(1))

    # Get manager objs
    service_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

    advertisement = AutoPiAdvertisement(bus, 0)
    obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")

    logger.info("Registering agent")
    capability = "NoInputNoOutput"
    agent_path = "/dimo/agent"
    agent = Agent(bus, agent_path)

    agent_manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    agent_manager.RegisterAgent(agent_path, capability)
    agent_manager.RequestDefaultAgent(agent_path)
    logger.info("Agent registered")
    # logger.info("Attempting to connect to trusted devices")

    # try:
    #     # device_paths = listDevices(logger)
    #     device_paths = ["/org/bluez/hci0/dev_F4_65_A6_D0_17_E0"]
    #     for device_path in device_paths:
    #         logger.info("Connecting to %s" % device_path)
    #         dev_connect(device_path)
    # except Exception as e:
    #     logger.error(traceback.format_exc())

    app = Application(bus)
    app.add_service(AutoPiS1Service(bus, 0))

    mainloop = MainLoop()

    ad_manager.RegisterAdvertisement(
        advertisement.get_path(),
        {},
        reply_handler=register_ad_cb,
        error_handler=register_ad_error_cb,
    )

    logger.info("Registering GATT application...")

    service_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=register_app_cb,
        error_handler=register_app_error_cb,
    )

    mainloop.run()


if __name__ == "__main__":
    main()
