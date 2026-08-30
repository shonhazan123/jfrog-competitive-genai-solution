FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
# Strip any CRLF line endings before making it executable. A checkout on Windows
# (core.autocrlf=true) can rewrite this script to CRLF, which makes the Linux
# container fail to start ("bad interpreter" / no such file or directory). This
# keeps the image working no matter how the repo was cloned.
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
