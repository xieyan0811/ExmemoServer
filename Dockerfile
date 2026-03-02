# Build: docker build -t exmemoserver:latest .
# Run: docker run --rm -it --net=host --env-file .env exmemoserver:latest
# Dev: docker-compose --profile development up

FROM python:3.11-slim

MAINTAINER XieYan

RUN apt-get update -y && \
    apt-get install -y git vim && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . /opt/exmemoserver

WORKDIR /opt/exmemoserver

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
