#!/bin/bash
# if [[ -n $YOUR_VARIABLE ]]; then
#   printenv
# fi
printenv
ls /github/workspace
python3.12 wiki-sync.py
