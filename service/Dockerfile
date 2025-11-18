FROM python:3.13-alpine3.22

ARG APP_PORT

WORKDIR /

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${APP_PORT}

CMD ["python", "main.py"]