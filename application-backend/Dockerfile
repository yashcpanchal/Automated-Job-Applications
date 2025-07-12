# Dockerfile for our FastAPI Secret Agent Brain

# Use an official Python runtime as a parent image.
# This is like saying: "Start with a standard Python workshop blueprint."
FROM python:3.13-slim-bookworm

# Set the working directory inside the container.
# This is like saying: "All our work for this workshop will happen in a folder called /app."
WORKDIR /app

# Prevent Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure output is streamed directly to the terminal without buffering
ENV PYTHONUNBUFFERED=1

# Install system dependencies required by Playwright browsers
# These are common dependencies for running headless browsers
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libsndfile1 \
#     libnss3 \
#     libfontconfig1 \
#     libatk-bridge2.0-0 \
#     libdrm-dev \
#     libgtk-3-0 \
#     libasound2 \
#     libsecret-1-0 \
#     libu2f-udev \
#     libvulkan1 \
#     libxkbcommon0 \
#     libxcomposite1 \
#     libxdamage1 \
#     libxext6 \
#     libxfixes3 \
#     libxrandr2 \
#     libxshmfence1 \
#     libxtst6 \
#     libgbm1 \
#     xdg-utils \
#     # Clean up apt caches to keep image size small
#     && rm -rf /var/lib/apt/lists/*

# Copy the Python dependency files into the container.
COPY requirements.txt .

# Install the Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install && playwright install-deps

# RUN playwright install-deps

# Copy the entire FastAPI application code into the container.
COPY . .

# Expose the port that Uvicorn will run on.
EXPOSE 8000

# Command to run the FastAPI application when the container starts.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]