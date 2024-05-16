# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements.txt file into the container at /usr/src/app/Ai
COPY Ai/requirements.txt ./Ai/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r ./Ai/requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Set the working directory to /usr/src/app/Ai
WORKDIR /usr/src/app/Ai

# Run discord_mixy.py when the container launches
CMD ["python", "./discord_mixy.py"]
