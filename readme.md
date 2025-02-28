# Wiki Sync GH Action


A GitHub action that does bi-directional sync between a docs folder in your repo and the GH
wiki for that repo.

Known issues:

1. The wiki repo has to exist.  Create at least one page manually through the UI before syncing.
   * **WARNING!! - do this before you add the sync action** if you have existing docs.  Otherwise, the
     first sync kicked off by creating the wiki will delete all your existing docs.  If that
     happens, just use git to revert that commit.
2. There is no GitHub action event for a wiki page delete (#1).  Delete pages from the doc side to
   avoid having them reappear.
3. Edit conflicts would likely result in a broken sync until resolved manually (#5).


## Usage Example

See `action.yaml` for other input options besides those listed below.

```yaml
name: Docs <-> Wiki

on:
  push:
    branches:
      # Name a branch "docs-preview" if you want commits to the branch to apply to the wiki
      # immediately. Helpful if you want to make multiple updates, preview them, merge commits, etc.
      # before finally merging to master.
      - docs-preview

      # With the above exception, doc updates will only by synced to the wiki when merged to the
      # default branch.
      #
      # TODO: confirm or change default branch name for your repo
      - main
    paths:
      # TODO: this should match where your wiki docs are synced to.  E.g. "docs/**"
      - "wiki/**"

  # gollum is the wiki add/update event and this only triggers for the default branch.  I.e. if
  # an update is made to the wiki, only the master branch will be updated.
  gollum:

# Limit this workflow to a single run at a time to avoid race conditions
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sync-docs:
    # Avoid cyclical sync when the wiki is updated.  GitHub has built-in protection for push event.
    if: github.event_name != 'gollum' || !contains(github.event.pages[0].summary, 'wiki sync bot:')
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v4

      - name: GitHub Wiki Sync
        uses: level12/gh-action-wiki-sync@main
        with:
          # TODO: change this if your docs are in a directory other than "wiki"
          # docs_path: wiki

          # TODO: change this to a personal access token secret for better security
          # github_token: ${{ github.token }}
```
