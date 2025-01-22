FROM xserrat/facebook-demucs:latest
WORKDIR /server

COPY requirement.txt /server/
COPY worker-server.py /server/

RUN pip3 install -r requirement.txt

ENTRYPOINT ["python3", "worker-server.py"]