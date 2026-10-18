import unittest

from fetcher.cli import main
from fetcher.settings import load


class FetcherTest(unittest.TestCase):
    def test_retries_setting(self):
        self.assertEqual(load({"retries": 1}).retries, 1)

    def test_cli_retries(self):
        calls = []

        def send(url, timeout):
            calls.append(url)
            raise ConnectionError

        client = main(["--retries", "1"], send)
        with self.assertRaises(ConnectionError):
            client.get("http://example.test")
        self.assertEqual(len(calls), 2)
