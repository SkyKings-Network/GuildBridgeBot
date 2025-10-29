FROM nikolaik/python-nodejs:python3.13-nodejs25

# Set the working directory in the container
WORKDIR /Bot

# Install deoendencies
COPY requirements.txt /Bot/requirements.txt
RUN pip install --no-cache-dir -r /Bot/requirements.txt
RUN npm install -g mineflayer

# Copy the application code into the container
COPY . /Bot

ENV IS_DOCKER=1
ENV PYTHONUNBUFFERED=1

# Define the command to run the application
CMD ["python3", "main.py"]