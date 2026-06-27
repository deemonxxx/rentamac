FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for paramiko and WireGuard tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    wireguard-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create SSH directory for connecting to Mac nodes
RUN mkdir -p /app/.ssh && chmod 700 /app/.ssh

EXPOSE 8000

# Run as root (needed for WireGuard operations and SSH key access)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
