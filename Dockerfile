FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
