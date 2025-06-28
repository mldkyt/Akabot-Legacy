FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY features /app/features
COPY utils /app/utils
COPY database.py /app
COPY main.py /app/
COPY lang/ /app/lang/
COPY configs/ /app/configs/

CMD ["python", "/app/main.py"]
