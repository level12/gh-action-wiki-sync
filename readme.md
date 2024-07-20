# Wiki Sync GH Action


A GitHub action that does bi-directional[^1] sync between a docs folder in your repo and the GH
wiki for that repo.

[^1]: GH wiki doesn't send delete events.  Delete docs from repo.


## Action Example

This repo uses the action.  See its action [sync-wiki.yaml](.github/workflows/wiki-sync.yaml) for
example usage.
