FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py data.py environment.py app.py inference.py openenv.yaml README.md analytics.py consequences.py index.html pyproject.toml ./
COPY server/ ./server/

ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
