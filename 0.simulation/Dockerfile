FROM python:3.12-slim

WORKDIR /app

COPY 0.simulation/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY 0.simulation/ ./

CMD ["python", "main.py"]
