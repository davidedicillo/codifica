FROM node:22-alpine AS web
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CODIFICA_DATABASE_PATH=/data/codifica.sqlite
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY server/ ./server/
COPY agent/ ./agent/
COPY --from=web /build/dist ./web/dist
RUN useradd --uid 10001 --create-home codifica && mkdir /data && chown codifica:codifica /data
USER codifica
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/health',headers={'Host':__import__('urllib.parse',fromlist=['urlparse']).urlparse(os.environ['CODIFICA_ORIGIN']).netloc}); urllib.request.urlopen(r,timeout=4)"
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
