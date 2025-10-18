FROM node:20-slim

# Install Python for the server
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy application files
COPY server_simple.py .

# Create directory for data
RUN mkdir -p /data

# Expose port
EXPOSE 8787

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8787
ENV PATH="/usr/local/bin:${PATH}"

# Volume for persistent data storage
VOLUME ["/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8787/health || exit 1

# Start the server
CMD ["python3", "server_simple.py"]
