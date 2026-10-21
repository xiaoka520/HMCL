#!/usr/bin/env python3
"""Exercise transient DMG failures with a simulated disk-image utility."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('create-dmg.sh')


class CreateDmgTests(unittest.TestCase):
    def run_case(self, failures, message='Resource busy', verify_status=0):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            utility = root / 'hdiutil'
            utility.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
root = Path(os.environ['DMG_TEST_ROOT'])
with (root / 'calls').open('a') as calls:
    calls.write(sys.argv[1] + '\\n')
if sys.argv[1] == 'verify':
    sys.exit(int(os.environ['DMG_TEST_VERIFY_STATUS']))
counter = root / 'counter'
attempt = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(attempt))
if attempt <= int(os.environ['DMG_TEST_FAILURES']):
    print('hdiutil: create failed - ' + os.environ['DMG_TEST_MESSAGE'], file=sys.stderr)
    sys.exit(16)
''')
            utility.chmod(0o755)
            sleeper = root / 'sleep'
            sleeper.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$DMG_TEST_ROOT/delays"\n')
            sleeper.chmod(0o755)
            environment = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                               DMG_TEST_ROOT=str(root), DMG_TEST_FAILURES=str(failures),
                               DMG_TEST_MESSAGE=message, DMG_TEST_VERIFY_STATUS=str(verify_status))
            result = subprocess.run(['bash', str(SCRIPT), 'HMCL app.app', 'image path.dmg'],
                                    env=environment, capture_output=True, text=True)
            calls = (root / 'calls').read_text().splitlines()
            delays = (root / 'delays').read_text().splitlines() if (root / 'delays').exists() else []
            return result, calls, delays

    def test_success_has_no_retry(self):
        result, calls, delays = self.run_case(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['create', 'verify'])
        self.assertEqual(delays, [])

    def test_busy_retries_then_verifies(self):
        result, calls, delays = self.run_case(2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['create', 'create', 'create', 'verify'])
        self.assertEqual(delays, ['5', '10'])

    def test_busy_exhaustion_preserves_failure(self):
        result, calls, delays = self.run_case(3)
        self.assertEqual(result.returncode, 16)
        self.assertEqual(calls, ['create'] * 3)
        self.assertEqual(delays, ['5', '10'])

    def test_other_error_is_not_retried(self):
        result, calls, delays = self.run_case(3, message='No space left on device')
        self.assertEqual(result.returncode, 16)
        self.assertEqual(calls, ['create'])
        self.assertEqual(delays, [])

    def test_verification_failure_is_not_hidden(self):
        result, calls, delays = self.run_case(0, verify_status=9)
        self.assertEqual(result.returncode, 9)
        self.assertEqual(calls, ['create', 'verify'])
        self.assertEqual(delays, [])


if __name__ == '__main__':
    unittest.main()
