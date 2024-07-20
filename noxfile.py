from pathlib import Path

import nox


package_path = Path.cwd()

# NOTE: uv is much faster at creating venvs and generally compatible with pip.
# Pip compat: https://github.com/astral-sh/uv/blob/main/PIP_COMPATIBILITY.md
nox.options.default_venv_backend = 'uv'


def test_run(session, *args):
    session.install('-r', 'requirements/base.txt')
    session.install('-e', '.')

    args = (*args, *session.posargs)
    session.run(
        'pytest',
        # Use our pytest.ini to isolate the test run from the
        '-c=ci/pytest.ini',
        '-ra',
        '--tb=native',
        '--strict-markers',
        '--cov=climate',
        '--cov-config=.coveragerc',
        '--cov-report=xml',
        '--no-cov-on-fail',
        '--report-permissions',
        f'--junit-xml={package_path}/ci/test-reports/{session.name}.pytests.xml',
        *args,
    )


def _test_migrations(session):
    migrations_dpath = Path('src/test_migrations')
    migration_count = len(list(migrations_dpath.glob('*.py')))
    if not migration_count:
        print('No migrations found')
        return

    test_run(
        session,
        migrations_dpath,
    )


@nox.session
def test_all(session: nox.Session):
    test_run(session, 'src/climate')
    _test_migrations(session)


@nox.session
def precommit(session: nox.Session):
    session.install('-c', 'requirements/dev.txt', 'pre-commit')
    session.run(
        'pre-commit',
        'run',
        '--all-files',
    )


@nox.session
def audit(session: nox.Session):
    # Much faster to install the deps first and have pip-audit run agains the venv
    session.install('-r', 'requirements/dev.txt')
    session.run(
        'pip-audit',
        '--desc',
        '--skip-editable',
    )


@nox.session
def alembic(session: nox.Session):
    session.install('-r', 'requirements/base.txt')
    session.run('python', 'scripts/count-heads')


# The following sessions are intended for CI and therefore don't run by default
@nox.session(default=False)
def test_part_calcs(session: nox.Session):
    test_run(
        session,
        'src/climate/residuals/tests/test_calc',
    )


@nox.session(default=False)
def test_part_remaining(session: nox.Session):
    test_run(
        session,
        '--ignore=src/climate/residuals/tests/test_calc',
        'src/climate',
    )


@nox.session(default=False)
def test_migrations(session: nox.Session):
    _test_migrations(session)
