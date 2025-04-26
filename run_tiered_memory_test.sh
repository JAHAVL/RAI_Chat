#!/bin/bash

# Script to run the tiered memory tests inside the Docker container
echo "=== Running Tiered Memory System Tests in Docker ==="

# Copy test files to the backend container
echo "Copying test files to Docker container..."
docker cp tests/test_tiered_memory_docker.py rai-backend:/app/tests/
docker cp tests/test_coherence_simple.py rai-backend:/app/tests/
docker cp tests/test_memory_api_quiz.py rai-backend:/app/tests/

# Run basic tests inside the container
echo "Running basic functionality tests..."
docker exec rai-backend python -m unittest /app/tests/test_tiered_memory_docker.py

# Run simple coherence tests 
echo "\nRunning simple coherence tests..."
docker exec rai-backend python -m unittest /app/tests/test_coherence_simple.py

# Run the API-based memory quiz test (ensure the API is running)
echo "\nRunning API-based memory quiz test..."
docker exec rai-backend python -m unittest /app/tests/test_memory_api_quiz.py

echo "=== Test run complete ==="
