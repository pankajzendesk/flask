# Use the official Python base image
FROM python:3.12-slim
RUN apt update -y
RUN apt-get update && apt-get install -y ansible ssh
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the SSH key for Ansible to use
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

# Make port 5001 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME FlaskApp

# Run app.py when the container launches
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0","--port=5000"]
