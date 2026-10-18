import unittest

from fetcher.cli import main
from fetcher.client import Client
from fetcher.settings import Settings, load


def failing(calls):
    def send(url, timeout):
        calls.append(timeout)
        raise ConnectionError
    return send


class FetcherAcceptance(unittest.TestCase):
    def test_ac1_settings(self):
        self.assertEqual(Settings().retries, 3)
        self.assertEqual(load({}).retries, 3)
        for bad in (-1, 1.5, "2"):
            with self.assertRaises(ValueError, msg=bad):
                load({"retries": bad})

    def test_ac2_client_attempts(self):
        for retries, expected in ((0, 1), (2, 3)):
            calls = []
            with self.assertRaises(ConnectionError):
                Client(load({"retries": retries}), failing(calls)).get("u")
            self.assertEqual(len(calls), expected)

    def test_ac2_success_stops_retrying(self):
        calls = []

        def flaky(url, timeout):
            calls.append(url)
            if len(calls) < 2:
                raise ConnectionError
            return "ok"

        self.assertEqual(Client(load({"retries": 5}), flaky).get("u"), "ok")
        self.assertEqual(len(calls), 2)

    def test_ac3_cli(self):
        calls = []
        client = main(["--retries", "0", "--timeout", "2"], failing(calls))
        with self.assertRaises(ConnectionError):
            client.get("u")
        self.assertEqual(calls, [2.0])
        calls = []
        with self.assertRaises(ConnectionError):
            main([], failing(calls)).get("u")
        self.assertEqual(len(calls), 4)
