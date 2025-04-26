#!/bin/bash

# Script to run the tiered memory tests inside the Docker container

echo "Starting Docker test for tiered memory system..."

# Make sure the Docker containers are running
docker-compose ps backend > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Docker containers are not running. Starting them now..."
    docker-compose up -d
    sleep 10  # Give containers time to start
fi

# Copy the test file into the backend container
docker cp tests/test_tiered_memory_simple.py rai-chat-backend:/app/tests/

# Run the test inside the Docker container where MySQL is accessible
docker exec -it rai-chat-backend python /app/tests/test_tiered_memory_simple.py

echo "Test completed."
