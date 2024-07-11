# Use the official Python image from the Docker Hub
FROM python:3.10.14-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN python -m pip install -r requirements.txt

# Copy the local files into the container
COPY . /app/

# Run the application
CMD ["python", "main.py"]