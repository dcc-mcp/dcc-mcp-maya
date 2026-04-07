# Import built-in modules
import os
import sys

# Import third-party modules
import nox

ROOT = os.path.dirname(__file__)

if ROOT not in sys.path:
    sys.path.append(ROOT)

# Import local modules
from nox_actions import codetest  # noqa: E402
from nox_actions import lint      # noqa: E402
from nox_actions import release   # noqa: E402

nox.session(lint.lint, name="lint")
nox.session(lint.lint_fix, name="lint-fix")
nox.session(codetest.pytest, name="pytest")
nox.session(release.make_install_zip, name="make-zip")
