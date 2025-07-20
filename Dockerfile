FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set entry point
CMD ["python", "main.py"]  # Change to your main script name
