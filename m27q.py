# For Gigabyte M27Q KVM connected over USB
#
# Based on: https://gist.github.com/wadimw/4ac972d07ed1f3b6f22a101375ecac41


import usb.core
import usb.util
from time import sleep
import typing as t
import sys

class MonitorControl:
    def __init__(self):
        self._VID = 0x2109  # (VIA Labs, Inc.)
        self._PID = 0x8883  # USB Billboard  usb.core.Device
        self._devs = []
        self._usb_delay = 50 / 1000  # 50 ms sleep after every usb op
        
    # Find USB  usb.core.Devices, set config
    def __enter__(self):
        self._devs = list(usb.core.find(idVendor=self._VID, idProduct=self._PID, find_all=True))
        if len(self._devs) == 0:
            raise IOError(f" usb.core.Device VID_{self._VID}&PID_{self._PID} not found")

        self._had_driver = {}

        for dev in self._devs:
            if sys.platform != "win32":
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
                    self._had_driver[dev] = True
            else:
                self._had_driver[dev] = False

            dev.set_configuration(1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for dev in self._devs:
            if self._had_driver[dev]:
                dev.attach_kernel_driver(0)

    def usb_write(self, dev:  usb.core.Device, b_request: int, w_value: int, w_index: int, message: bytes):
        bm_request_type = 0x40
        if not dev.ctrl_transfer(
            bm_request_type, b_request, w_value, w_index, message
        ) == len(message):
            raise IOError("Transferred message length mismatch")
        sleep(self._usb_delay)

    def usb_read(self, dev:  usb.core.Device, b_request: int, w_value: int, w_index: int, msg_length: int):
        bm_request_type = 0xC0
        data = dev.ctrl_transfer(
            bm_request_type, b_request, w_value, w_index, msg_length
        )
        sleep(self._usb_delay)
        return data
        
    def get_osd(self, dev:  usb.core.Device, data: t.List[int]):
        self.usb_write(
            dev=dev,
            b_request=178,
            w_value=0,
            w_index=0,
            message=bytearray([0x6E, 0x51, 0x81 + len(data), 0x01]) + bytearray(data),
        )
        data = self.usb_read(dev=dev, b_request=162, w_value=0, w_index=111, msg_length=12)
        return data[10]

    def set_osd(self, dev:  usb.core.Device, data: bytearray):
        self.usb_write(
            dev=dev,
            b_request=178,
            w_value=0,
            w_index=0,
            message=bytearray([0x6E, 0x51, 0x81 + len(data), 0x03] + data),
        )

    def set_brightness(self, dev:  usb.core.Device, brightness: int):
        self.set_osd(
            [
                0x10,
                0x00,
                max(self._min_brightness, min(self._max_brightness, brightness)),
            ]
        )

    def get_brightness(self, dev:  usb.core.Device):
        return self.get_osd(dev, [0x10])

    def transition_brightness(self, dev:  usb.core.Device, to_brightness: int, step: int = 3):
        current_brightness = self.get_brightness(dev)
        diff = abs(to_brightness - current_brightness)
        if current_brightness <= to_brightness:
            step = 1 * step  # increase
        else:
            step = -1 * step  # decrease
        while diff >= abs(step):
            current_brightness += step
            self.set_brightness(dev, current_brightness)
            diff -= abs(step)
        # Set one last time
        if current_brightness != to_brightness:
            self.set_brightness(dev, to_brightness)

    def set_volume(self, dev:  usb.core.Device, volume: int):
        return self.set_osd(dev, [0x62, 0x00, volume])

    def get_volume(self, dev:  usb.core.Device):
        return self.get_osd(dev, [0x62])

    def get_kvm_status(self, dev:  usb.core.Device):
        return self.get_osd(dev, [224, 105])

    def set_kvm_status(self, dev:  usb.core.Device, status):
        self.set_osd(dev, [224, 105, status])

    def toggle_kvm(self, dev:  usb.core.Device):
        self.set_kvm_status(dev, 1 - self.get_kvm_status(dev))
        
    def get_devices(self) ->  usb.core.Device:
        return self._devs
        
if __name__ == "__main__":
    with MonitorControl() as m:
        for dev in m.get_devices():
            m.set_kvm_status(dev=dev, status=1)
