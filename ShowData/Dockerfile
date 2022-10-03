FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "main:app"]
EXPOSE 5000

