FROM python:3.12-slim

WORKDIR /app

COPY 1.intel_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/

COPY 1.intel_service/ ./

CMD ["python", "main.py"]
