from pathlib import Path

import nox


package_path = Path.cwd()

# NOTE: uv is much faster at creating venvs and generally compatible with pip.
# Pip compat: https://github.com/astral-sh/uv/blob/main/PIP_COMPATIBILITY.md
nox.options.default_venv_backend = 'uv'


@nox.session
def tests(session: nox.Session):
    session.install('-r', 'requirements/test.txt')
    session.install('-e', '.')
    session.run(
        'pytest',
        # use our pytest.ini for warning management
        '-c=ci/pytest.ini',
        '-ra',
        '--tb=native',
        '--strict-markers',
        'src',
        *session.posargs,
    )


@nox.session
def standards(session: nox.Session):
    session.install('-c', 'requirements/dev.txt', 'pre-commit')
    session.run(
        'pre-commit',
        'run',
        '--all-files',
    )
