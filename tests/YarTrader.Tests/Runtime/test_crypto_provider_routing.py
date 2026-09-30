import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.Data.Providers.Crypto.crypto_provider import CryptoProvider
from src.Infrastructure.exceptions import ValidationException


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


class CryptoProviderRoutingTests(unittest.TestCase):
    def test_long_window_is_chunked_and_returns_real_candles(self):
        provider = CryptoProvider()
        calls = []

        def fake_urlopen(request, timeout=10):
            calls.append(request.full_url)
            base = 83000 + len(calls) * 100
            return _Response([[int(datetime(2026, 9, 1, 0, 0).timestamp()), base - 10, base + 10, base, base + 5, 1.0]])

        end = datetime(2026, 9, 30)
        start = end - timedelta(days=30)
        with patch('src.Data.Providers.Crypto.crypto_provider.urllib.request.urlopen', side_effect=fake_urlopen):
            candles = provider.fetch_real_candles('BTCUSD', 'M15', start, end)

        self.assertGreater(len(calls), 1)
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].close, 84005.0)
        self.assertNotEqual(candles[0].close, 60000.0)

    def test_provider_does_not_fallback_to_synthetic_data(self):
        provider = CryptoProvider()
        with patch(
            'src.Data.Providers.Crypto.crypto_provider.urllib.request.urlopen',
            side_effect=RuntimeError('network unavailable'),
        ):
            with self.assertRaises(ValidationException):
                provider.fetch_real_candles(
                    'BTCUSD',
                    'M15',
                    datetime(2026, 9, 29),
                    datetime(2026, 9, 30),
                )


if __name__ == '__main__':
    unittest.main()
