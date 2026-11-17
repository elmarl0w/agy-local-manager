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

    def test_hash_fingerprint(self):
        with tempfile.TemporaryDirectory() as root:
            f = Path(root) / 'file'
            f.write_text('test')
            self.assertEqual(len(m.sha(f)), 64)

if __name__ == '__main__':
    unittest.main()
