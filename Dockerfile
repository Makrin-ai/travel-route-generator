FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=src/travel_app/app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "src/travel_app/app.py"]
ARG SECRET_KEY=default_key
ENV SECRET_KEY=$SECRET_KEY
