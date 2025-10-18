FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY token_manager.py .
COPY start_with_refresh.py .

# Create directory for tokens
RUN mkdir -p /data

# Expose port
EXPOSE 8787

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8787

# Volume for persistent token storage
VOLUME ["/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8787/health')"

# Run the application with token refresh
CMD ["python3", "start_with_refresh.py"]