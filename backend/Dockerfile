FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=sqlite:////data/app.db
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir diskcache==5.6.3 \
    && python -c "import diskcache; from litellm.caching import Cache; print('LiteLLM cache dependencies OK')"
COPY app ./app
RUN mkdir -p /data && chmod 777 /data
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
