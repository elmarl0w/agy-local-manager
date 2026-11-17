import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts/patch_adapter.py'
spec = importlib.util.spec_from_file_location('adapter_patch', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FIXTURE = '''    write_file: {
        primaryKey: 'AbsolutePath',
    },
    read_file: {
        primaryKey: 'AbsolutePath',
    },
    const config = TOOL_PARAM_NORMALIZATION[name];
    if (!config) {
        return applyUniversalPathFallback(args);
    }
    const normalized = {};
    return normalized;
}
function applyUniversalPathFallback(args)
return { name: 'write_file', args: { AbsolutePath: absPath, Content: content, Append: cmd.includes('>>') } };
'''

class AdapterPatchTest(unittest.TestCase):
    def test_patches_expected_symbols(self):
        result = m.patch_text(FIXTURE)
        self.assertIn("primaryKey: 'Path'", result)
        self.assertIn('args.toolSummary', result)
        self.assertIn("name: 'write_file', args: { Path: absPath", result)
        self.assertEqual(result, m.patch_text(result), 'Patch must be idempotent')

    def test_node_accepts_temporary_js_extension(self):
        if not shutil.which('node'):
            self.skipTest('Node.js unavailable')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'utils.js'
            temporary = target.with_name(target.stem + '.new.js')
            temporary.write_text('const answer = 42;\n')
            self.assertEqual(temporary.suffix, '.js')
            subprocess.run(['node', '--check', str(temporary)], check=True)

    def test_rejects_unknown_upstream(self):
        with self.assertRaises(ValueError):
            m.patch_text('totally different version')

if __name__ == '__main__':
    unittest.main()
