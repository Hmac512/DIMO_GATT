import array
import dbus.exceptions

from gatt.ble import Descriptor
import os
# from web3 import Web3


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.InvalidValueLength"


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.Failed"


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.
    """

    CUD_UUID = "2901"

    def __init__(
        self, bus, index, characteristic,
    ):

        self.value = array.array("B", characteristic.description)
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index, self.CUD_UUID, [
                            "read"], characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


def getEnvVars():
    # OWNER_ETH_ADDRESS = os.getenv("OWNER_ETH_ADDRESS")
    # COMMUNICATION_PUBLIC_KEY = os.getenv("COMMUNICATION_PUBLIC_KEY")

    # if not(OWNER_ETH_ADDRESS and Web3.isAddress(OWNER_ETH_ADDRESS)):
    #     OWNER_ETH_ADDRESS = None
    # if not(COMMUNICATION_PUBLIC_KEY and Web3.isAddress(COMMUNICATION_PUBLIC_KEY)):
    #     COMMUNICATION_PUBLIC_KEY = None

    OWNER_ETH_ADDRESS = None
    COMMUNICATION_PUBLIC_KEY = None
    if OWNER_ETH_ADDRESS and COMMUNICATION_PUBLIC_KEY:
        IS_PAIRED = True
    else:
        IS_PAIRED = False

    return (IS_PAIRED, OWNER_ETH_ADDRESS, COMMUNICATION_PUBLIC_KEY)
