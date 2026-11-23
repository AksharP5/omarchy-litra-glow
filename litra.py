#!/usr/bin/env python3
"""Control a Logitech Litra Glow through its hidraw node."""

import json
import os
import select
import sys
from pathlib import Path
from typing import NotRequired, TypedDict

HID_ID = "0003:0000046D:0000C900"
BRIGHTNESS = (20, 250)  # lumens
TEMPERATURE = (2700, 6500)  # kelvin, in steps of 100
REPLY_SECONDS = 1.0
POLL_SECONDS = 2.0


class Status(TypedDict):
    connected: bool
    error: str
    on: NotRequired[bool]
    brightness: NotRequired[int]
    temperature: NotRequired[int]


def find_device(root: Path = Path("/sys/class/hidraw")) -> Path | None:
    # The hidraw number changes across replugs and boots, so match the HID ID.
    for node in sorted(root.glob("hidraw*")):
        try:
            uevent = (node / "device" / "uevent").read_text().splitlines()
        except OSError:
            continue
        if f"HID_ID={HID_ID}" in uevent:
            return Path("/dev") / node.name
    return None


def clamp(value: int, limits: tuple[int, int]) -> int:
    return max(limits[0], min(limits[1], value))


class Litra:
    def __init__(self, fd: int):
        self.fd = fd

    @classmethod
    def open(cls, path: Path) -> "Litra":
        return cls(os.open(path, os.O_RDWR))

    def close(self) -> None:
        os.close(self.fd)

    def request(self, function: int, *data: int) -> bytes:
        os.write(self.fd, bytes([0x11, 0xFF, 0x04, function, *data]).ljust(20, b"\0"))
        header = bytes([0x11, 0xFF, 0x04, function])
        while True:
            if not select.select([self.fd], [], [], REPLY_SECONDS)[0]:
                raise TimeoutError("Litra Glow did not respond")
            reply = os.read(self.fd, 64)
            # Skip reports meant for another request, such as a late ack.
            if reply[:4] == header:
                return reply

    def status(self) -> Status:
        power = self.request(0x01)
        brightness = self.request(0x31)
        temperature = self.request(0x81)
        return {
            "connected": True,
            "error": "",
            "on": power[4] == 1,
            "brightness": int.from_bytes(brightness[4:6]),
            "temperature": int.from_bytes(temperature[4:6]),
        }

    def run(self, command: list[str]) -> None:
        match command:
            case ["power", "on" | "off" as state]:
                self.request(0x1C, state == "on")
            case ["power", "toggle"]:
                self.request(0x1C, self.request(0x01)[4] != 1)
            case ["brightness", value]:
                self.request(0x4C, *clamp(int(value), BRIGHTNESS).to_bytes(2))
            case ["temperature", value]:
                kelvin = clamp(round(int(value), -2), TEMPERATURE)
                self.request(0x9C, *kelvin.to_bytes(2))
            case _:
                raise ValueError(f"Unknown command: {' '.join(command)}")


def latest(commands: list[list[str]]) -> list[list[str]]:
    # A dragged slider sends many values; only the last of each kind matters.
    # Power commands all run, so two quick toggles still cancel out.
    return [
        command for index, command in enumerate(commands)
        if command[0] == "power" or all(later[0] != command[0] for later in commands[index + 1:])
    ]


def disconnected(error: str = "") -> Status:
    return {"connected": False, "error": error}


def watch(stdin: int = 0, find=find_device) -> None:
    """Print status as JSON lines; apply commands read from stdin as they arrive."""
    light: Litra | None = None
    last: Status | None = None
    buffered = b""
    while True:
        commands: list[list[str]] = []
        if select.select([stdin], [], [], POLL_SECONDS)[0]:
            chunk = os.read(stdin, 4096)
            if not chunk:
                return
            *lines, buffered = (buffered + chunk).split(b"\n")
            commands = [line.decode().split() for line in lines if line.strip()]

        status = disconnected()
        try:
            if light is None and (path := find()) is not None:
                light = Litra.open(path)
            if light is not None:
                errors = []
                for command in latest(commands):
                    try:
                        light.run(command)
                    except ValueError as error:
                        errors.append(str(error))
                status = {**light.status(), "error": "\n".join(errors)}
        except OSError as error:
            if light is not None:
                light.close()
                light = None
            status = disconnected(error.strerror or str(error))

        # Always answer a command, so the bar replaces its optimistic value.
        if status != last or commands:
            print(json.dumps(status), flush=True)
            last = status


def main(args: list[str]) -> int:
    if args == ["watch"]:
        watch()
        return 0
    path = find_device()
    if path is None:
        print(json.dumps(disconnected()))
        return 1
    light = Litra.open(path)
    try:
        if args and args != ["status"]:
            light.run(args)
        print(json.dumps(light.status()))
    finally:
        light.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
