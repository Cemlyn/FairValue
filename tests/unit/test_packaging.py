import os
import subprocess
import sys

import fairvalue

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(fairvalue.__file__)))


def test_import_outside_repo_root(tmp_path):
    """The package must not depend on files relative to the working directory."""
    result = subprocess.run(
        [sys.executable, "-c", "import fairvalue.models"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": REPO_ROOT},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
