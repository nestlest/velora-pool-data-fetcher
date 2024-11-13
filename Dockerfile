FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install python-dotenv to load environment variables from .env file
RUN pip3 install python-dotenv

# Copy the rest of the application code and .env file
COPY . .

# Command to run the application
CMD ["python3", "main.py"]
