# FinPort — production container image
FROM python:3.11-slim

# Streamlit needs these for healthchecks and proper signal handling
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install dependencies first so the layer is cached across code changes
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application source
COPY . .

# Run as a non-root user (security best practice)
RUN useradd --create-home --uid 1000 finport && chown -R finport:finport /app
USER finport

EXPOSE 8501

# Container healthcheck hits Streamlit's built-in health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8501/_stcore/health').status==200 else sys.exit(1)"

ENTRYPOINT ["streamlit", "run", "app.py"]
