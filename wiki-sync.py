from os import environ
from pathlib import Path
import shutil
import subprocess
import sys


gh_repo = environ.get('REPOSITORY')
run_sync = environ.get('INPUT_RUN-SYNC')
docs_dpath = environ.get('DOCS_DIR')
workspace_dpath = environ.get('GITHUB_WORKSPACE')
tmp_wiki_dpath = Path('/tmp/gh-wiki-sync')
commit_user: str = environ.get('COMMIT_USER')
commit_email: str = environ.get('COMMIT_EMAIL')
is_gh_action: bool = bool(environ.get('GITHUB_ACTIONS', False))
gh_api_token = environ.get('GH_API_TOKEN')


def stderr(text):
    print(text, file=sys.stderr)


def sub_run(*args, capture=False, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault('check', True)
    kwargs.setdefault('capture_output', capture)
    args = args + kwargs.pop('args', ())
    return subprocess.run(args, **kwargs)


def gh_wiki_repo():
    if is_gh_action:
        return f'https://x-access-token:{gh_api_token}@github.com/{gh_repo}.wiki.git'

    return f'git@github.com:{gh_repo}.wiki.git'


class Git:
    def __init__(self, repo_path: Path):
        self.repo_path: Path = repo_path
        self.config(commit_user, commit_email)

    def __call__(self, *args, **kwargs):
        return self.git(*args, **kwargs)

    def config(self, user: str, email: str = ''):
        if not is_gh_action:
            # Local dev, don't mess with the config
            return

        user = user or environ.get('USER', 'DocSync Action')
        email = email or 'devteam+gh-actions@level12.io'
        self.git('config', 'user.name', user)
        self.git('config', 'user.email', email)

    def git(self, *args, in_repo=True, **kwargs):
        cwd_path = self.repo_path if in_repo else None
        return sub_run('git', args=args, cwd=cwd_path, **kwargs)


def rsync(src: Path, dest: Path):
    sub_run('rsync', '-ac', '--delete', f'{src}/', dest, '--exclude', '.git')


def main(ctx: click.Context, update: str):
    if not run_sync:
        print('Confiugred to not run sync. Exiting early')
        return

    if tmp_wiki_dpath.exists():
        shutil.rmtree(tmp_wiki_dpath)
    tmp_wiki_dpath.mkdir(parents=True)

    print('commit_user', commit_user)
    print('commit_email', commit_email)
    print('is_gh_action', is_gh_action)

    wiki_repo = gh_wiki_repo()
    print('wiki repo', wiki_repo)
    sub_run('git', 'clone', '--single-branch', '--depth=1', wiki_repo, tmp_wiki_dpath)

    if update == 'wiki':
        rsync(f'{docs_dpath}/', tmp_wiki_dpath)
        git = Git(tmp_wiki_dpath)
        git('add', '.')
        message = 'update wiki from docs'
        push_args = '--set-upstream', wiki_repo
    else:
        # Updating docs

        # Prep to use the last wiki commit message in the commit we make in the main repo
        log_result = Git(tmp_wiki_dpath).git('log', '-1', '--pretty=%B', capture=True)
        wiki_commit_msg = log_result.stdout.decode('utf-8', errors='replace').strip()
        if wiki_commit_msg.startswith('docs sync bot:'):
            # We are in a loop.  The if: statement in the action should prevent this but no
            # harm in being careful.
            print('Loop detected.  The last wiki commit was from this sync action.  Exiting.')
            return

        rsync(f'{tmp_wiki_dpath}/', docs_dpath)
        git = Git(workspace_dpath)
        # In the action, there should be no other changes in the repo.  But, when testing locally,
        # we'd only want to push changes in the docs directory.
        git('add', docs_dpath)
        message = f'update docs from wiki\n\n{wiki_commit_msg}'
        push_args = ()

    result = git('diff', '--cached', '--exit-code', check=False)
    if result.returncode not in (0, 1):
        ctx.fail('`git diff` returned unexpected exit code')

    if result.returncode == 1:
        # --no-verify only really matters when running locally
        git('commit', '-m', f'docs sync bot: {message}\n\n[skip ci]', '--no-verify')
        git('push', *push_args)
        print('Changes pushed')
    else:
        print('No changes')


if __name__ == '__main__':
    main()
