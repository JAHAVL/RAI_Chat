# RAI Chat Application - Docker Setup

This document outlines how to run the RAI Chat application using Docker. Dockerizing the application provides a consistent environment and resolves dependency issues.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup Instructions

1. **Set Environment Variables**

   Each component requires its own environment variables. Copy the example files and fill in your actual values:

   ```bash
   # For LLM Engine
   cp llm_Engine/.env.example llm_Engine/.env
   
   # For Backend
   cp RAI_Chat/backend/.env.example RAI_Chat/backend/.env
   ```

   Edit each `.env` file with the appropriate values:
   
   **LLM Engine (.env)**:
   - `GEMINI_API_KEY` - Google Gemini API key for the LLM
   
   **Backend (.env)**:
   - `TAVILY_API_KEY` - Required for web search functionality
   - `JWT_SECRET` - For authentication security

2. **Build and Start the Application**

   Run the following command to build and start all services:

   ```bash
   docker-compose up --build
   ```

   To run the services in the background (detached mode):

   ```bash
   docker-compose up --build -d
   ```

3. **Access the Application**

   Once all the services are running, you can access the application at:
   - Frontend: http://localhost:8081
   - Backend API: http://localhost:6102
   - LLM Engine: http://localhost:6101

4. **Monitoring and Logs**

   View logs for all services:

   ```bash
   docker-compose logs -f
   ```

   View logs for a specific service:

   ```bash
   docker-compose logs -f backend
   docker-compose logs -f llm-engine
   docker-compose logs -f frontend
   ```

5. **Stopping the Application**

   To stop all running services:

   ```bash
   docker-compose down
   ```

## Troubleshooting

- **Ports Already in Use**: If you see "Address already in use" errors, ensure no existing processes are using ports 6101, 6102, or 8081, or modify the port mappings in the docker-compose.yml file.

- **Network Issues**: If services can't connect to each other, check the Docker network settings.

- **Environment Variables**: Ensure all required environment variables are correctly set in your `.env` file.

## Benefits of using Docker for RAI Chat

- **Consistent Environment**: Docker ensures all components run in the same environment, resolving import and dependency issues.

- **Isolated Services**: Each component (LLM Engine, Backend, Frontend) runs in its own container, preventing conflicts.

- **Simplified Setup**: New developers can get started quickly with just Docker installed, without configuring Python versions or dependencies.

- **Improved Development Experience**: Changes to code are immediately reflected without having to restart services manually.

- **Easy Deployment**: The Dockerized application can be deployed to any environment supporting Docker.

## Architecture

- **llm-engine**: Provides the LLM API
- **backend**: Flask backend with web search capabilities
- **frontend**: React frontend application

The services are networked together through the `rai-network` Docker network, with volumes configured for persistent data storage.
