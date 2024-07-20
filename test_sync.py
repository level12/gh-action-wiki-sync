from dataclasses import dataclass
from os import environ
from pathlib import Path

from sync_utils import Git, project_dpath, sub_run


wiki_sync_py = project_dpath / 'wiki-sync.py'


@dataclass
class SyncResult:
    stdout: str
    stderr: str
    code: str

    def __str__(self):
        return f"""
Exit code: {self.code}
STDOUT:
    {self.stdout}
STDERR:
    {self.stderr}
"""


class Env:
    def __init__(self, tmp_path: Path):
        # docs repo: i.e. github hosted repo
        self.docs_repo: Git = Git(tmp_path / 'docs-repo')
        self.docs_repo.repo_path.joinpath('wiki').mkdir(parents=True)
        self.docs_repo.git('init')
        self.docs_repo.git('config', 'user.name', 'docs user')
        self.docs_repo.git('config', 'user.email', 'docs@example.com')

        # wiki repo: i.e. github hosted wiki repo
        self.wiki_repo: Git = Git(tmp_path / 'wiki-repo')
        self.wiki_repo.repo_path.mkdir()
        self.wiki_repo.git('init')
        self.wiki_repo.git('config', 'user.name', 'wiki user')
        self.wiki_repo.git('config', 'user.email', 'wiki@example.com')

        # workspace repo: i.e. the working repo that would be checked out by the workflow and
        # be mounted in the docker container.
        self.workspace_repo: Git = Git(tmp_path / 'workspace-repo')
        self.workspace_repo.clone_from(self.docs_repo.repo_path)
        self.workspace_repo.repo_path.joinpath('wiki').mkdir(parents=True)
        self.workspace_repo.git('config', 'user.name', 'workspace user')
        self.workspace_repo.git('config', 'user.email', 'workspace@example.com')

    def sync(self, event_name: str, *sync_args, run_sync: bool = True, check=True):
        check = False if run_sync is False else check

        env = environ | {
            'GITHUB_WORKSPACE': str(self.workspace_repo.repo_path),
            'WIKI_REPO_PATH': str(self.wiki_repo.repo_path),
            'GITHUB_REPOSITORY': 'level12/gh-action-wiki-sync',
            'INPUT_DOCS_PATH': 'wiki',
            'INPUT_RUN_SYNC': 'true' if run_sync else 'false',
            'GITHUB_EVENT_NAME': event_name,
        }
        result = sub_run(wiki_sync_py, *sync_args, env=env, capture=True, check=False)
        result = SyncResult(
            result.stdout.decode('utf-8', errors='replace').strip(),
            result.stderr.decode('utf-8', errors='replace').strip(),
            result.returncode,
        )

        if check and result.code != 0:
            raise Exception(str(result))

        return result


class TestLocal:
    def test_bad_event(self, tmp_path):
        env = Env(tmp_path)
        result = env.sync('foo', check=False)
        assert result.stdout == ''
        assert result.stderr == 'Unexpected event: foo'
        assert result.code == 1

    def test_no_run(self, tmp_path):
        env = Env(tmp_path)
        result = env.sync('foo', run_sync=False)
        assert result.stdout == ''
        assert result.stderr == 'Confiugred to not run sync. Exiting.'
        assert result.code == 1

    def test_print_wiki_repo(self, tmp_path):
        env = Env(tmp_path)
        result = env.sync('push', '--print-wiki-repo', check=False)
        assert result.stdout == f'Wiki repo: {env.wiki_repo.repo_path}'
        assert result.stderr == 'Only printing wiki repo'
        assert result.code == 1

    def test_wiki_update(self, tmp_path):
        env = Env(tmp_path)
        env.workspace_repo.add_file('wiki/Home.md')

        env.wiki_repo.make_bare()
        result = env.sync('push')

        lines = result.stdout.splitlines()
        assert lines.pop(0) == f'Wiki repo: {env.wiki_repo.repo_path}'
        assert lines.pop(0) == 'Changes pushed'

        result = env.sync('push')
        lines = result.stdout.splitlines()
        assert lines.pop(0) == f'Wiki repo: {env.wiki_repo.repo_path}'
        assert lines.pop(0) == 'No changes'

        commit = env.wiki_repo.last_commit()
        assert commit.user == 'workspace user'
        assert commit.email == 'workspace@example.com'
        assert (
            commit.message
            == """
wiki sync bot: update from add_file()

Picard > Kirk

Action: update wiki from docs
[skip ci]
""".strip()
        )

        env.wiki_repo.make_working()
        assert env.wiki_repo.repo_path.joinpath('Home.md').read_text() == 'World'

    def test_docs_update(self, tmp_path):
        env = Env(tmp_path)
        env.wiki_repo.add_file('Home.md')

        env.docs_repo.make_bare()
        result = env.sync('gollum')

        lines = result.stdout.splitlines()
        assert lines.pop(0) == f'Wiki repo: {env.wiki_repo.repo_path}'
        assert lines.pop(0) == 'Changes pushed'

        result = env.sync('push')
        lines = result.stdout.splitlines()
        assert lines.pop(0) == f'Wiki repo: {env.wiki_repo.repo_path}'
        assert lines.pop(0) == 'No changes'

        commit = env.docs_repo.last_commit()
        assert commit.user == 'wiki user'
        assert commit.email == 'wiki@example.com'
        assert (
            commit.message
            == """
wiki sync bot: update from add_file()

Picard > Kirk

Action: update docs from wiki
[skip ci]
""".strip()
        )

        env.docs_repo.make_working()
        assert env.docs_repo.repo_path.joinpath('wiki/Home.md').read_text() == 'World'
