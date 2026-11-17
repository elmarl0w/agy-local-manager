import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / 'agy_manager.py'
spec = importlib.util.spec_from_file_location('agy_manager', FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManagerTest(unittest.TestCase):
    def test_source_binary_custom_path(self):
        with tempfile.TemporaryDirectory() as root:
            binary = Path(root) / 'agy'
            binary.write_text('#!/bin/sh\n')
            binary.chmod(0o755)
            with patch.object(m, 'settings', return_value={'system_agy': str(binary)}):
                self.assertEqual(m.source_binary(), binary)

    def test_proxy_port_busy_uses_loopback(self):
        class ActiveConnection:
            def __enter__(self): return self
            def __exit__(self, *args): return None
        with patch.object(m.socket, 'create_connection', return_value=ActiveConnection()) as conn:
            self.assertTrue(m.proxy_port_busy())
            conn.assert_called_once_with(('127.0.0.1', 50998), timeout=0.3)

    def test_verbose_flag_is_forwarded(self):
        with patch.object(m, 'launch') as launch, patch.object(m.sys, 'argv', ['agy', '--verbose']):
            self.assertEqual(m.main(), 0)
            launch.assert_called_once_with(['--verbose'])

    def test_hash_fingerprint(self):
        with tempfile.TemporaryDirectory() as root:
            f = Path(root) / 'file'
            f.write_text('test')
            self.assertEqual(len(m.sha(f)), 64)

if __name__ == '__main__':
    unittest.main()
