from dataclasses import dataclass
import logging
from os import environ
from pathlib import Path
import subprocess
import sys


logging.basicConfig(level=logging.INFO)

proj_src_dpath = Path(__file__).parent


def sub_run(*args, capture=False, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault('check', True)
    kwargs.setdefault('capture_output', capture)
    args = args + kwargs.pop('args', ())
    return subprocess.run(args, **kwargs)


def stderr(*args):
    print(*args, file=sys.stderr)


def bool_env(env_key: str):
    val = environ.get(env_key, '')
    return val.lower() in ('true', 't', '1', 'enable', 'on')


@dataclass
class CommitMeta:
    user: str
    email: str
    message: str

    @property
    def author(self):
        return f'{self.user} <{self.email}>'


class Git:
    def __init__(self, repo_path: Path):
        self.repo_path: Path = repo_path
        self.commit: CommitMeta | None = None

    def __call__(self, *args, **kwargs):
        return self.git(*args, **kwargs)

    def last_commit(self):
        result = self.git('log', '-1', '--pretty=format:%an|||%ae|||%B', capture=True)

        return CommitMeta(
            *result.stdout.decode('utf-8', errors='replace').strip().split('|||'),
        )

    def git(self, *args, in_repo=True, **kwargs):
        cwd_path = self.repo_path if in_repo else None
        return sub_run('git', args=args, cwd=cwd_path, **kwargs)

    def clone_from(self, src_path: Path):
        sub_run('git', 'clone', '--single-branch', '--depth=1', src_path, self.repo_path)

    def add_file(self, fpath: str, text: str = 'World'):
        self.repo_path.joinpath(fpath).write_text(text)
        self.git('add', '-A')
        self.git('commit', '-m', 'update from add_file()\n\nPicard > Kirk')

    def make_bare(self):
        self.git('config', '--bool', 'core.bare', 'true')
        [path.unlink() for path in self.repo_path.glob('*.md')]

    def make_working(self):
        self.git('config', '--bool', 'core.bare', 'false')
        self.git('checkout')

    def safe(self):
        self.git('config', '--global', '--add', 'safe.directory', self.repo_path)
