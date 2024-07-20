from python:3.12

copy wiki-sync.py entrypoint.sh /

entrypoint ["bash", "/entrypoint.sh"]
