FROM python:3.11-slim


RUN useradd -m appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .


USER appuser

EXPOSE 5000


HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=5)" || exit 1

CMD ["python", "app.py"]