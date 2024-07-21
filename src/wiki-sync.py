#!/usr/bin/env python
from os import environ
from pathlib import Path
import shutil
import sys

import click
from sync_utils import Git, bool_env, sub_run


VERSION = '0.1.0'

is_gh_action: bool = bool_env('GITHUB_ACTIONS')
gh_repo = environ['GITHUB_REPOSITORY']
run_sync = bool_env('INPUT_RUN_SYNC')
docs_rel_path = environ['INPUT_DOCS_PATH']
gh_token = environ.get('INPUT_GITHUB_TOKEN')
event_name = environ['GITHUB_EVENT_NAME']

workspace_dpath = Path(environ['GITHUB_WORKSPACE'])
docs_dpath = workspace_dpath / docs_rel_path
tmp_wiki_dpath = Path('/tmp/gh-wiki-sync')
commit_msg_prefix = 'wiki sync bot:'
commit_msg = """
{prefix} {src_message}

Action: {message}
[skip ci]
""".strip()


def fail(text):
    print(text, file=sys.stderr)
    sys.exit(1)


def gh_wiki_repo():
    if is_gh_action:
        if token_len := len(gh_token):
            print('Token length:', token_len)
        else:
            fail('Running in action but GITHUB_TOKEN was empty.')

        return f'https://x-access-token:{gh_token}@github.com/{gh_repo}.wiki.git'

    return environ.get('WIKI_REPO_PATH', f'git@github.com:{gh_repo}.wiki.git')


def rsync(src: Path, dest: Path):
    sub_run('rsync', '-ac', '--delete', f'{src}/', dest, '--exclude', '.git')


@click.command()
@click.option('--print-wiki-repo', is_flag=True)
def main(print_wiki_repo: bool | None):
    if not run_sync:
        fail('Confiugred to not run sync. Exiting.')

    if event_name not in ('push', 'gollum'):
        fail(f'Unexpected event: {event_name}')

    if tmp_wiki_dpath.exists():
        shutil.rmtree(tmp_wiki_dpath)
    tmp_wiki_dpath.mkdir(parents=True)

    wiki_repo = gh_wiki_repo()

    print('Wiki repo:', wiki_repo)
    if print_wiki_repo:
        fail('Only printing wiki repo')

    sub_run('git', 'clone', '--single-branch', '--depth=1', wiki_repo, tmp_wiki_dpath)

    if event_name == 'push':
        # push event: update wiki
        rsync(f'{docs_dpath}/', tmp_wiki_dpath)

        git = Git(tmp_wiki_dpath)
        git('add', '.')
        message = 'update wiki from docs'
        push_args = '--set-upstream', wiki_repo
        src_commit = Git(workspace_dpath).last_commit()
    else:
        src_commit = Git(tmp_wiki_dpath).last_commit()
        # gollum (gh wiki) event: update src docs
        if src_commit.message.startswith(commit_msg_prefix):
            # We are in a loop.  The if: statement in the action should prevent this but no
            # harm in being careful.
            print('Loop detected.  The last wiki commit was from this sync action.  Exiting.')
            return

        rsync(f'{tmp_wiki_dpath}/', docs_dpath)
        git = Git(workspace_dpath)
        # In the action, there should be no other changes in the repo.  But, when testing locally,
        # we'd only want to push changes in the docs directory.
        git('add', docs_dpath)
        message = 'update docs from wiki'
        push_args = ()

    result = git('diff', '--cached', '--exit-code', check=False, stdout=sys.stderr)
    if result.returncode not in (0, 1):
        fail('`git diff` returned unexpected exit code')

    if result.returncode == 1:
        msg = commit_msg.format(
            prefix=commit_msg_prefix,
            message=message,
            src_message=src_commit.message,
        )
        git('commit', '-m', msg, '--author', src_commit.author, stdout=sys.stderr)
        git('push', *push_args, stdout=sys.stderr)
        print('Changes pushed')
    else:
        print('No changes')


if __name__ == '__main__':
    main()
