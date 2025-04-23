#!/bin/bash
# Script to build and run RAI Chat in Docker

set -e  # Exit on any error

# Display header
echo "=========================================="
echo "RAI Chat Docker Setup and Run Script v1.3.1"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "Error: Docker or Docker Compose is not installed or not running. Please install Docker Desktop first."
    exit 1
fi

# Function to check if .env files exist and create them from examples if not
check_env_files() {
    local env_files=(
        "./llm_Engine/.env"
        "./RAI_Chat/backend/.env"
        "./RAI_Chat/frontend/.env"
    )
    
    local env_examples=(
        "./llm_Engine/.env.example"
        "./RAI_Chat/backend/.env.example"
        "./RAI_Chat/frontend/.env.example"
    )
    
    for i in "${!env_files[@]}"; do
        if [ ! -f "${env_files[$i]}" ]; then
            if [ -f "${env_examples[$i]}" ]; then
                echo "Creating ${env_files[$i]} from example file..."
                cp "${env_examples[$i]}" "${env_files[$i]}"
                echo "Please edit ${env_files[$i]} with your configuration values."
            else
                echo "Warning: ${env_examples[$i]} does not exist. Please create ${env_files[$i]} manually."
            fi
        fi
    done
}

# Function to check if Tavily API key is set in backend .env file
check_tavily_api_key() {
    local backend_env="./RAI_Chat/backend/.env"
    
    if [ -f "$backend_env" ]; then
        if ! grep -q "TAVILY_API_KEY=" "$backend_env" || grep -q "TAVILY_API_KEY=$" "$backend_env"; then
            echo "\nWARNING: TAVILY_API_KEY is not set in $backend_env"
            echo "Web search functionality will not work without a valid Tavily API key."
            echo "Please edit $backend_env and add your Tavily API key."
            echo "You can get a free API key at https://tavily.com\n"
            
            read -p "Do you want to continue without web search functionality? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Exiting. Please set up the Tavily API key and try again."
                exit 1
            fi
        else
            echo "Tavily API key found in $backend_env. Web search should be available."
        fi
    fi
}

# Check and create .env files if needed
check_env_files

# Check if Tavily API key is set
check_tavily_api_key

# Create necessary directories for Docker volumes
echo "Creating necessary directories for Docker volumes..."
mkdir -p ./RAI_Chat/backend/data/logs
mkdir -p ./llm_Engine/logs
mkdir -p ./llm_Engine/data

# Build the Docker images
echo "Building Docker images..."
docker compose build

# Run the Docker containers
echo "Starting RAI Chat containers..."
docker compose up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 5

# Display container status
echo "Container status:"
docker compose ps

# Check if containers are running
if docker compose ps | grep -q "Up"; then
    echo ""
    echo "✅ RAI Chat is now running in Docker!"
    echo "Access the application at: http://localhost:8081"
    echo "Backend API is available at: http://localhost:6102/api"
    echo "LLM Engine API is available at: http://localhost:6101/api"
    echo ""
    echo "To view logs, run: docker compose logs -f"
    echo "To stop the application, run: docker compose down"
    echo ""
    echo "NOTE: The first startup may take a minute or two while the services initialize."
    echo "If you encounter any issues, check the logs with: docker-compose logs -f"
 else
    echo ""
    echo "⚠️ Some containers may not have started properly."
    echo "Check the logs with: docker compose logs -f"
    echo "You can try restarting with: docker compose restart"
 fi
