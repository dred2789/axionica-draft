"""Exercise deployment on Linux (GNU mv and flock), without SSH."""
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(__import__('sys').platform.startswith('linux'), 'GNU/Linux deployment script')
class DeployTest(unittest.TestCase):
    def test_switch_removes_previous_only_after_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            def run(name, valid=True):
                incoming = base / name
                incoming.mkdir()
                payload = base / 'payload'
                payload.mkdir(exist_ok=True)
                for file in ('index.html', 'en/index.html', '404.html'):
                    target = payload / file
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(name)
                with tarfile.open(incoming / 'website.tar.gz', 'w:gz') as archive:
                    if valid:
                        archive.add(payload, arcname='.')
                return subprocess.run(['sh', str(ROOT / 'deploy/release.sh')],
                                      env={**os.environ, 'DEPLOY_PATH': directory, 'DEPLOY_RELEASE': name},
                                      capture_output=True, text=True)
            self.assertEqual(run('incoming-1-1').returncode, 0)
            self.assertEqual(os.readlink(base / 'current'), 'incoming-1-1')
            self.assertNotEqual(run('incoming-2-1', False).returncode, 0)
            self.assertEqual(os.readlink(base / 'current'), 'incoming-1-1')
            self.assertEqual(run('incoming-3-1').returncode, 0)
            self.assertEqual(os.readlink(base / 'current'), 'incoming-3-1')
            self.assertFalse((base / 'incoming-1-1').exists())
            self.assertFalse((base / 'incoming-2-1').exists())
            self.assertFalse((base / 'incoming-3-1/website.tar.gz').exists())

    def test_rejects_untrusted_release_name(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['sh', str(ROOT / 'deploy/release.sh')],
                                    env={**os.environ, 'DEPLOY_PATH': directory, 'DEPLOY_RELEASE': '../outside'},
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
