#!/bin/bash
set -e

echo "==== RAI Chat Docker Deployment ===="
echo "Setting up Docker environment..."

# Run the environment setup script if .env files don't exist
if [ ! -f "RAI_Chat/backend/.env" ] || [ ! -f "llm_Engine/.env" ] || [ ! -f "RAI_Chat/frontend/.env" ]; then
  echo "Setting up environment files..."
  ./setup_docker_env.sh
  echo ""
  echo "IMPORTANT: Please edit the .env files to add your API keys before continuing."
  echo "Press Enter when you've updated the API keys..."
  read -p ""
fi

# Build and start the Docker containers
echo "Building and starting Docker containers..."
docker compose build
docker compose up -d

# Wait for services to be ready
echo "Waiting for services to start up..."
sleep 10

# Check if services are running
echo "Checking services status..."
docker compose ps

echo ""
echo "==== RAI Chat Application is now running! ===="
echo "Frontend: http://localhost:8081"
echo "Backend API: http://localhost:6102"
echo "LLM Engine: http://localhost:6101"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
