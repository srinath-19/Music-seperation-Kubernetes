FROM python:3.8.2-alpine

WORKDIR /server

COPY requirements.txt /server/
COPY rest-server.py /server/

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python", "rest-server.py"]