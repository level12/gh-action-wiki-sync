from python:3.12

workdir /action

copy src src
copy requirements/base.txt .

run python -m pip install -r base.txt

entrypoint ["python", "/action/src/wiki-sync.py"]
cmd []
