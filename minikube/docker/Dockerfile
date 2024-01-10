FROM python:3.11
COPY entrypoint.sh /entrypoint
COPY entrypoint.py /entrypoint.py
RUN PYTHONUNBUFFERED=1 python /entrypoint.py install
