from typing import Dict, List
from bleak import BleakScanner
from bleak import BleakClient
from bleak.backends.device import BLEDevice
import logging
from crccheck.crc import Crc8Maxim


class Oximeter:

    def __init__(self, address=None):
        self._client = BleakClient(address)
        self._wave_callback = None
        self._data_callback = None
        self._mode_callback = None
        self._raw_callback = None
        self._last_battery = 100
        self._undecoded = bytearray()

    async def find(self, name="PC-60F") -> List[BLEDevice]:
        """Gets the near devices .

            Args:
                name = Device name.
            Returns:
                A list of the devices that the scanner has discovered during the scanning.
        """
        logging.info("Scanning for peripherals...")

        devices = await BleakScanner.discover(10)
        result  = []
        for d in devices:
            logging.info(str(d).split("(b'")[0])
            if str(d).split("(b'")[0].find(name) > 0:
                result.append(d)

        return result

    def setaddres(self, address) -> None:
        """Set device address .

            Args:
                address = Device address.
        """
        self._client.address = address

    async def run(self) -> bool:
        """Start reciving data from device.


            Return boolen runing status
        """
        try:
            await self._client.connect()
            logging.info("Connected to Device {0}".format(
                self._client.address))

            for service in self._client.services:
                logging.debug("[Service] {0}: {1}".format(
                    service.uuid, service.description))

            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await self._client.read_gatt_char(char.uuid))
                    except Exception as e:
                        value = str(e).encode()
                else:
                    value = None
                logging.debug(
                    "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                        char.uuid,
                        char.handle,
                        ",".join(char.properties),
                        char.description,
                        value,
                    ))
            await self._client.start_notify(service.characteristics[1], self._notification_handler)

            return True
        except:
            return False

    def flush(self) -> None:
        """Remove all undecoded data

        """
        self._undecoded.clear()

    def decode(self, data: bytearray) -> Dict:
        """Decode raw bytearray data.

            Args:
                data = byteattay to decode 
            Returns:
                Dictionary with specific data 
        """

        return_dict = dict(wave=list(), data=list(),
                           mode=list(), undecded=bytearray())

        for communique in data.split(b'\xaa\x55'):
            communique = b'\xaa\x55'+communique

            if(len(communique) > 2):
                try:
                    if not communique[3] == len(communique[4:]):
                        return_dict["undecded"] += communique
                        continue
                    elif Crc8Maxim.calcbytes(communique[:-1])[0] != communique[-1]:
                        logging.warning("[COM] {0} {1}".format(
                            Crc8Maxim.calcbytes(communique[:-1]), communique.hex(" ")))
                        continue
                except:
                    return_dict["undecded"] += communique
                    continue

                if communique[4] == 2:
                    logging.debug("[WAVE] {0}".format(
                        communique[5:-1].hex(" ")))
                    # [(raw wave data)x5]
                    for x in communique[3:-1]:
                        return_dict["wave"].append(int(x))
                    if (self._wave_callback):
                        self._wave_callback(communique[5:-1])

                elif communique[4] == 1:
                    logging.debug("[DATA] {0}".format(
                        communique[5:-1].hex(" ")))
                    # [(battery 0-3),crc8 maxim]
                    return_dict["data"].append(dict(
                        spo2=communique[5], hr=communique[6], pi=communique[8]/10, battery=self._last_battery))
                    if (self._data_callback):
                        self._data_callback(return_dict["data"][-1])

                elif communique[4] == 3:
                    logging.debug("[BAT] {0}".format(
                        communique[5:-1].hex(" ")))
                    # [(battery 0-3),crc8 maxim]
                    self._last_battery = int(communique[5]*100/3)

                elif communique[4] == 33:
                    logging.debug("[MODE] {0}".format(
                        communique[5:-1].hex(" ")))
                    # [(mode 1:spot check 2:continuous),(function 0:continuous 2:measurment 3:data 4:status 5:end cycle),(0:continuous, time to the end of the measurement/spo2,errorcode:status),(0/HR),crc8 maxim)

                    return_dict["mode"].append(dict(mode=communique[5], func=communique[6], data=[
                                               communique[7], communique[8]]))

                    if (self._mode_callback):
                        self._mode_callback(return_dict["mode"][-1])

        return return_dict

    def _notification_handler(self, sender: int, data: bytearray):
        logging.info("Recive {0} byte from {1}".format(len(data), sender))
        logging.debug("Byte array {0}".format(data.hex(" ")))
        if self._raw_callback:
            self._raw_callback(data)
        else:
            self._undecoded = self.decode(self._undecoded+data)["undecded"]

    def setWave_callback(self, callback) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept one inputs, list with data.

        Args:
        callback (function): The function to be called on notification.

        """

        self._wave_callback = callback

    def setData_callback(self, callback) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept one input dictionary with data.

        Args:
        callback (function): The function to be called on notification.

        """

        self._data_callback = callback

    def setMode_callback(self, callback) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept one input dictionary with data.

        Args:
        callback (function): The function to be called on notification.

        """

        self._mode_callback = callback

    def setRaw_callback(self, callback) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept one input byteattay.

        Args:
        callback (function): The function to be called on notification.

        """

        self._raw_callback = callback
