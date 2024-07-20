from python:3.12

workdir /action

copy src src

entrypoint ["python", "/action/src/wiki-sync.py"]
