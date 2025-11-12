FROM python:3-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY immich-folder-albums.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT [ "/app/immich-folder-albums.py" ]
