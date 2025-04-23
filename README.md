# R.AI Chat Application

A modern chat application with offline message support and intelligent assistant capabilities, including web search functionality.

## Features

- Real-time chat with AI assistants
- Web search integration via Tavily API
- Offline message queuing and synchronization
- Responsive UI design
- Message persistence
- System notifications for connectivity status

## Project Structure

- `/frontend` - React frontend application
  - `/src` - Source code
    - `/api` - API client and service interfaces
    - `/components` - Reusable UI components
    - `/pages` - Page components
    - `/services` - Business logic services
    - `/utils` - Utility functions
- `/RAI_Chat/Backend` - Flask backend server
  - `/api` - API endpoints
  - `/components` - Business logic components
  - `/services` - Service layer
  - `/modules` - Feature modules including web search
- `/llm_Engine` - LLM API server for handling AI model interactions

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- Python 3.9 or higher
- npm or yarn
- Tavily API key (for web search functionality)

### Environment Setup

1. Create a `.env` file in the `/RAI_Chat/Backend` directory with the following variables:
```
TAVILY_API_KEY=your_tavily_api_key_here
```

### Installation

1. Clone the repository
```
git clone <repository-url>
cd RAI_Chat
```

2. Install dependencies
```
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../Backend
pip install -r requirements.txt

# Install LLM Engine dependencies
cd ../../llm_Engine
pip install -r requirements.txt
```

### Starting the Application

#### Option 1: Using Docker (Recommended)

The easiest and most reliable way to run the application is using Docker:

```bash
# Make the Docker scripts executable
chmod +x setup_docker_env.sh docker-start.sh

# Start the application with Docker
./docker-start.sh
```

This script will:
1. Set up the necessary environment files (if they don't exist)
2. Build the Docker images for all components
3. Start all services with Docker Compose
4. Configure networking between components automatically

Once started, you can access the application at http://localhost:8081 in your browser.

To view logs:
```bash
docker compose logs -f
```

To stop all containers:
```bash
docker compose down
```

#### Option 2: Using the local start script

If you prefer not to use Docker, you can use the provided start script:

```bash
# Make the script executable (if needed)
chmod +x start_app.sh

# Run the start script
./start_app.sh
```

This script will:
1. Start the LLM Engine on port 6101
2. Start the Backend Server on port 6102
3. Start the Frontend on port 8081
4. Monitor all components and provide logging

Once started, you can access the application at http://localhost:8081 in your browser.

To stop all components, press Ctrl+C in the terminal where the script is running.

#### Option 3: Manual startup

If you prefer to start components individually:

1. Start the LLM Engine
```
cd llm_Engine
python llm_api_server.py --port 6101
```

2. Start the Backend Server
```
cd RAI_Chat/Backend
python wsgi.py
```

3. Start the Frontend
```
cd RAI_Chat/frontend
npm start
```

## Development

### Frontend

The frontend is built with React and uses:
- TypeScript for type safety
- Styled Components for styling
- Axios for API requests
- Local storage for message persistence

### Backend

The backend is built with Flask and uses:
- SQLAlchemy for database interactions
- Flask-CORS for handling cross-origin requests
- JWT for authentication

### LLM Engine

The LLM Engine provides an API for interacting with various language models.

## Web Search Functionality

The application integrates with the Tavily API to provide web search capabilities. When a user asks a question that requires up-to-date information, the system can:

1. Detect when web search is needed
2. Perform a search using the Tavily API
3. Process and incorporate the search results into the AI's response

To use this feature:
- Ensure you have a valid Tavily API key in your `.env` file
- Ask questions that might benefit from web search, such as current events or factual information

## Troubleshooting

If you encounter issues starting the application:

1. Check the log files in the `/logs` directory
2. Ensure all required ports (6101, 6102, 8081) are available
3. Verify that all environment variables are set correctly
4. If web search isn't working:
   - Check that your Tavily API key is valid and properly set in the `.env` file
   - Look for any error messages in the backend logs related to the Tavily client

## License

This project is proprietary and confidential.
