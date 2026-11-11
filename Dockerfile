# Use an official Python runtime as a parent image
FROM python:3.12-slim
# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
# Install any needed packages specified in requirements.txt
CMD ls -l /app
RUN pip install -r ./requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 9800

# Run mimirr.py when the container launches
CMD ["python", "mimir_exporter.py"]
