FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt /app/

RUN apk add --no-cache git bash
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY .git/ .git/.
COPY docker/ docker/.
COPY features /app/features
COPY utils /app/utils
COPY database.py /app
COPY main.py /app/
COPY lang/ /app/lang/
COPY configs/ /app/configs/

RUN chmod +x docker/prepare.sh
RUN bash docker/prepare.sh

RUN apk --no-cache del git bash

CMD ["python", "/app/main.py"]
