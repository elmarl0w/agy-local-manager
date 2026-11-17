import shutil
import subprocess
from pathlib import Path
import unittest

JS = Path(__file__).resolve().parents[1] / 'scripts/quiet_startup.cjs'


class QuietStartupTest(unittest.TestCase):
    def test_known_noise_is_hidden_but_warnings_remain(self):
        if not shutil.which('node'):
            self.skipTest('Node.js unavailable')
        js = """
process.stdout.write('[Warn] agy 1.5.9 has not been tested with free-antigravity-cli. Latest tested: 1.0.0.\\n');
process.stdout.write('Starting proxy... ');
process.stdout.write('ready (port 50998)\\n');
process.stderr.write('[WARN] Port 50998 in use, falling back to dynamic port...\\n');
process.stdout.write('Antigravity CLI 1.5.9\\n');
"""
        proc = subprocess.run(['node', '--require', str(JS), '-e', js], capture_output=True, text=True, check=True)
        self.assertEqual(proc.stdout, 'Antigravity CLI 1.5.9\n')
        self.assertIn('Port 50998 in use', proc.stderr)


if __name__ == '__main__':
    unittest.main()
