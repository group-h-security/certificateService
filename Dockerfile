FROM python:3.12-slim

WORKDIR /app

COPY src/ .
COPY CertsAndKeys/ ./CertsAndKeys/

RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000

ENV PYTHONUNBUFFERED=1
CMD ["python", "CAServer.py"]

