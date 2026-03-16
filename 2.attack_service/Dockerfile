FROM python:3.12-slim

WORKDIR /app

COPY 2.attack_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY 2.attack_service/ ./

CMD ["python", "main.py"]
