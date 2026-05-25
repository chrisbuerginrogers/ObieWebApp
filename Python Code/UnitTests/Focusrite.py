"""
Focusrite Scarlett 4th Gen - Cross-platform gain control via USB HID
Uses the reverse-engineered Scarlett2 protocol (same as Linux kernel driver)

Install: pip install hid
On Mac:  brew install hidapi
On Windows: hidapi DLL is bundled with the `hid` package
On Linux: sudo apt install libhidapi-hidraw0
"""
import os
import ctypes

ctypes.CDLL("/opt/homebrew/lib/libhidapi.dylib")  # force-load it first

import hid
import hid  # all other imports below this

import struct
import time

# --- Focusrite Device IDs ---
FOCUSRITE_VENDOR_ID = 0x1235

SCARLETT_4TH_GEN_PRODUCTS = {
    0x8211: "Scarlett Solo 4th Gen",
    0x8210: "Scarlett 2i2 4th Gen",
    0x821C: "Scarlett 4i4 4th Gen",
}

# --- Scarlett2 USB HID Protocol Constants ---
# Based on the reverse-engineered scarlett2 protocol
# Ref: https://github.com/torvalds/linux/blob/master/sound/usb/mixer_scarlett2.c

SCARLETT2_USB_VENDOR_SPECIFIC_CLASS = 0xFF
SCARLETT2_USB_INTERRUPT_INTERVAL    = 8

# HID Report IDs
REPORT_ID_GET = 0x12
REPORT_ID_SET = 0x13

# Protocol header
SEQ_START    = 0x00
OPCODE_GET   = 0x60
OPCODE_SET   = 0x61
PAD          = 0x00

# Preamp gain control base address (4th Gen)
# Each channel is offset by 4 bytes
PREAMP_GAIN_BASE_ADDR = 0x0130

# Gain range: 0–69 (represents 0 dB to +69 dB, i.e. 1 dB steps)
GAIN_MIN = 0
GAIN_MAX = 69

# Per-model input channel count
INPUT_CHANNELS = {
    0x8211: 1,  # Solo:  1 preamp
    0x8210: 2,  # 2i2:   2 preamps
    0x821C: 4,  # 4i4:   4 preamps
}


class ScarlettGainController:
    def __init__(self):
        self.device = None
        self.product_id = None
        self.product_name = None
        self.num_channels = None
        self._seq = 0

    # ------------------------------------------------------------------
    # Device Management
    # ------------------------------------------------------------------

    def find_devices(self) -> list[dict]:
        """List all connected Scarlett 4th Gen devices."""
        found = []
        for pid, name in SCARLETT_4TH_GEN_PRODUCTS.items():
            for info in hid.enumerate(FOCUSRITE_VENDOR_ID, pid):
                found.append({
                    "product_id": pid,
                    "name": name,
                    "path": info["path"],
                    "serial": info.get("serial_number", ""),
                    "usage_page": info.get("usage_page", 0),
                })
        return found

    def connect(self, product_id: int = None, path: bytes = None):
        """
        Connect to a Scarlett device.
        Optionally specify product_id or HID path for disambiguation.
        """
        devices = self.find_devices()
        if not devices:
            raise RuntimeError("No Scarlett 4th Gen device found. Is it plugged in?")

        # Filter by product_id if given
        if product_id:
            devices = [d for d in devices if d["product_id"] == product_id]
            if not devices:
                raise RuntimeError(f"No device found with product_id 0x{product_id:04X}")

        target = next((d for d in devices if d["path"] == path), devices[0]) if path else devices[0]

        self.device = hid.device()
        self.device.open_path(target["path"])
        self.device.set_nonblocking(False)

        self.product_id   = target["product_id"]
        self.product_name = target["name"]
        self.num_channels = INPUT_CHANNELS[self.product_id]

        print(f"Connected to: {self.product_name} (serial: {target['serial']})")
        print(f"  Input preamp channels: {self.num_channels}")

    def disconnect(self):
        if self.device:
            self.device.close()
            self.device = None
            print("Disconnected.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ------------------------------------------------------------------
    # Low-level Scarlett2 Protocol
    # ------------------------------------------------------------------

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFF
        return self._seq

    def _build_get_report(self, address: int, length: int = 4) -> bytes:
        """
        Build a HID feature report to READ a control value.
        Scarlett2 GET packet format (32 bytes):
          [report_id, seq, 0x00, opcode, length(2), address(2), pad...]
        """
        seq = self._next_seq()
        payload = struct.pack(
            "<BBBBHH",
            REPORT_ID_GET,   # report ID
            seq,             # sequence number
            PAD,             # reserved
            OPCODE_GET,      # opcode: read
            length,          # data length in bytes
            address,         # control address
        )
        # Pad to 64 bytes (HID report size for Scarlett)
        payload = payload.ljust(64, b'\x00')
        return payload

    def _build_set_report(self, address: int, value: int) -> bytes:
        """
        Build a HID feature report to WRITE a control value.
        Scarlett2 SET packet format:
          [report_id, seq, 0x00, opcode, length(2), address(2), value(4), pad...]
        """
        seq = self._next_seq()
        payload = struct.pack(
            "<BBBBHHi",
            REPORT_ID_SET,
            seq,
            PAD,
            OPCODE_SET,
            4,           # 4-byte value
            address,
            value,
        )
        payload = payload.ljust(64, b'\x00')
        return payload

    def _send_and_recv(self, report: bytes) -> bytes:
        """Send a feature report and read the response."""
        # prepend 0x00 (report ID for write on some platforms)
        self.device.write(b'\x00' + report)
        time.sleep(0.02)  # give device time to respond
        response = bytes(self.device.read(64, timeout_ms=1000))
        if not response:
            raise TimeoutError("No response from device.")
        return response

    def _parse_int_response(self, response: bytes) -> int:
        """Extract a signed 32-bit integer from bytes 8–12 of the response."""
        return struct.unpack_from("<i", response, 8)[0]

    # ------------------------------------------------------------------
    # Gain Address Helpers
    # ------------------------------------------------------------------

    def _gain_address(self, channel: int) -> int:
        """Return the HID address for the given channel's preamp gain (0-indexed)."""
        self._validate_channel(channel)
        return PREAMP_GAIN_BASE_ADDR + (channel * 4)

    def _validate_channel(self, channel: int):
        if not (0 <= channel < self.num_channels):
            raise ValueError(
                f"Channel {channel} out of range. "
                f"{self.product_name} has {self.num_channels} preamp channel(s) (0-indexed)."
            )

    def _validate_gain(self, gain_db: int):
        if not (GAIN_MIN <= gain_db <= GAIN_MAX):
            raise ValueError(f"Gain {gain_db} dB out of range [{GAIN_MIN}, {GAIN_MAX}].")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_gain(self, channel: int) -> int:
        """
        Read the preamp gain for a channel (0-indexed).
        Returns gain in dB (0–69).
        """
        self._validate_channel(channel)
        addr    = self._gain_address(channel)
        report  = self._build_get_report(addr)
        resp    = self._send_and_recv(report)
        gain_db = self._parse_int_response(resp)
        return gain_db

    def set_gain(self, channel: int, gain_db: int):
        """
        Set the preamp gain for a channel (0-indexed).
        gain_db: integer 0–69 (dB).
        """
        self._validate_channel(channel)
        self._validate_gain(gain_db)
        addr   = self._gain_address(channel)
        report = self._build_set_report(addr, gain_db)
        self._send_and_recv(report)
        print(f"  Channel {channel} gain set to {gain_db} dB")

    def get_all_gains(self) -> list[int]:
        """Read gains for all preamp channels. Returns a list of dB values."""
        gains = []
        for ch in range(self.num_channels):
            gains.append(self.get_gain(ch))
        return gains

    def set_all_gains(self, gain_db: int):
        """Set the same gain on all preamp channels."""
        self._validate_gain(gain_db)
        for ch in range(self.num_channels):
            self.set_gain(ch, gain_db)

    def print_status(self):
        """Pretty-print current gain settings."""
        print(f"\n{self.product_name} — Preamp Gains")
        print("-" * 35)
        gains = self.get_all_gains()
        for i, g in enumerate(gains):
            bar = "█" * (g // 3)
            print(f"  Ch {i+1}: {g:>3} dB  {bar}")
        print()


# ------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------

if __name__ == "__main__":
    ctrl = ScarlettGainController()

    # List what's connected
    devices = ctrl.find_devices()
    if not devices:
        print("No Scarlett 4th Gen found.")
    else:
        print("Found devices:")
        for d in devices:
            print(f"  {d['name']}  (PID: 0x{d['product_id']:04X}, serial: {d['serial']})")

    # Use as a context manager for safe open/close
    with ScarlettGainController() as sc:

        # Read all gains
        sc.print_status()

        # Set channel 0 to 40 dB
        sc.set_gain(channel=0, gain_db=40)

        # Set channel 1 to 55 dB (if 2i2 / 4i4)
        # sc.set_gain(channel=1, gain_db=55)

        # Set all channels to 30 dB
        sc.set_all_gains(30)

        # Read back to confirm
        sc.print_status()
