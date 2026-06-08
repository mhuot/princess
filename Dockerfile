FROM python:3.14-slim

RUN useradd --create-home --uid 10001 princess
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY princess/ princess/
COPY static/ static/

RUN chown -R princess:princess /app
USER princess

ENV HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "princess"]
