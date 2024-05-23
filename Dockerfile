FROM python:3.8-slim

WORKDIR /app

COPY monitor.py /app/monitor.py
COPY config.template.yaml /app/templates/config.template.yaml

RUN pip install docker pyyaml croniter

CMD ["python", "monitor.py"]