import io
import json
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from litra import Litra, find_device, latest, watch


def report(*data):
    return bytes([0x11, 0xFF, 0x04, *data]).ljust(20, b"\0")


class LitraTests(unittest.TestCase):
    def setUp(self):
        # A packet socket keeps report boundaries, like a hidraw node.
        self.host, self.device = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(self.host.close)
        self.addCleanup(self.device.close)
        self.light = Litra(self.host.fileno())

    def answer(self, *replies):
        for reply in replies:
            self.device.send(reply)

    def sent(self):
        self.device.setblocking(False)
        reports = []
        while True:
            try:
                reports.append(self.device.recv(64))
            except BlockingIOError:
                return reports

    def test_finds_light_by_hid_id_not_node_number(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for node, hid_id in {"hidraw0": "0003:0000046D:0000C52B", "hidraw10": "0003:0000046D:0000C900"}.items():
                (root / node / "device").mkdir(parents=True)
                (root / node / "device" / "uevent").write_text(f"DRIVER=hid-generic\nHID_ID={hid_id}\n")
            self.assertEqual(find_device(root), Path("/dev/hidraw10"))
            (root / "hidraw10" / "device" / "uevent").unlink()
            self.assertIsNone(find_device(root))

    def test_status_decodes_replies_and_skips_stray_reports(self):
        self.answer(report(0x4C), report(0x01, 1), report(0x31, 0x00, 0xFA), report(0x81, 0x19, 0x64))
        self.assertEqual(self.light.status(), {
            "connected": True, "error": "", "on": True, "brightness": 250, "temperature": 6500,
        })

    def test_values_are_clamped_and_temperature_snaps_to_hundreds(self):
        self.answer(report(0x4C), report(0x9C), report(0x9C))
        self.light.run(["brightness", "300"])
        self.light.run(["temperature", "4049"])
        self.light.run(["temperature", "9000"])
        self.assertEqual(self.sent(), [report(0x4C, 0x00, 0xFA), report(0x9C, 0x0F, 0xA0), report(0x9C, 0x19, 0x64)])

    def test_toggle_reads_the_light_instead_of_trusting_a_cache(self):
        self.answer(report(0x01, 0), report(0x1C))
        self.light.run(["power", "toggle"])
        self.assertEqual(self.sent(), [report(0x01), report(0x1C, 1)])

    def test_slider_bursts_collapse_but_every_toggle_runs(self):
        commands = [["brightness", "40"], ["power", "toggle"], ["brightness", "90"], ["power", "toggle"], ["temperature", "3000"]]
        self.assertEqual(latest(commands), [["power", "toggle"], ["brightness", "90"], ["power", "toggle"], ["temperature", "3000"]])

    def test_unplugged_light_reports_disconnected_without_exiting(self):
        self.device.close()
        stdin, writer = os.pipe()
        os.write(writer, b"brightness 100\n")
        os.close(writer)
        output = io.StringIO()
        with patch.object(Litra, "open", return_value=self.light), redirect_stdout(output):
            watch(stdin, find=lambda: Path("/dev/hidraw10"))
        os.close(stdin)
        self.host.detach()  # watch closed the lost light's descriptor.
        status = json.loads(output.getvalue())
        self.assertFalse(status["connected"])
        self.assertNotEqual(status["error"], "")

    def test_bad_command_is_reported_alongside_real_state(self):
        stdin, writer = os.pipe()
        os.write(writer, b"brightness max\n")
        os.close(writer)
        self.answer(report(0x01, 0), report(0x31, 0x00, 0x14), report(0x81, 0x0A, 0x8C))
        output = io.StringIO()
        with patch.object(Litra, "open", return_value=self.light), redirect_stdout(output):
            watch(stdin, find=lambda: Path("/dev/hidraw10"))
        os.close(stdin)
        status = json.loads(output.getvalue())
        self.assertEqual((status["on"], status["brightness"], status["temperature"]), (False, 20, 2700))
        self.assertIn("max", status["error"])


if __name__ == "__main__":
    unittest.main()
