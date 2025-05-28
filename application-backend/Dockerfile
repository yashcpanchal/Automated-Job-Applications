# Dockerfile for our FastAPI Secret Agent Brain

# Use an official Python runtime as a parent image.
# This is like saying: "Start with a standard Python workshop blueprint."
FROM python:3.13-slim-bookworm

# Set the working directory inside the container.
# This is like saying: "All our work for this workshop will happen in a folder called /app."
WORKDIR /app

# Copy the Python dependency files into the container.
# This is like saying: "Bring the list of tools my robot needs (requirements.txt) into the workshop."
# We copy it before the actual code so Docker can cache this step.
COPY requirements.txt .

# Install the Python dependencies.
# This is like saying: "Now, actually install all those tools listed in requirements.txt."
# We install them inside the Docker container's environment.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire FastAPI application code into the container.
# This is like saying: "Now, bring my main.py (the robot's brain code) into the workshop."
COPY . .

# Expose the port that Uvicorn will run on.
# This is like saying: "This workshop will listen for messages on port 8000."
EXPOSE 8000

# Command to run the FastAPI application when the container starts.
# This is like saying: "When the workshop opens, automatically start Uvicorn to run the brain."
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]