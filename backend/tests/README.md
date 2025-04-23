# AI Assistant Test Suite

This directory contains test scripts for various components of the AI Assistant application. The tests are organized into categories based on their functionality.

## API Tests

Tests related to API communication with the Ollama LLM service.

- **test_ollama_api.py**: Tests the connection to the Ollama API and identifies the correct endpoint configuration.
- **test_llm_response.py**: Tests the generation of responses from the Ollama API using different models.
- **test_conversation_manager.py**: Tests the `_generate_llm_response` method of the ConversationManager class.

## Memory Tests

Tests related to the contextual memory system.

- **test_contextual_memory.py**: Tests the three-tier contextual memory system for storing and retrieving information.
- **test_memory_reset.py**: Tests that new chat sessions start with empty contextual memory.
- **test_new_chat_memory.py**: Tests the memory isolation between different chat sessions.

## Video Tests

Tests related to video processing and storage.

- **test_video_memory.py**: Tests the storage and retrieval of video information in the memory system.
- **test_video_session.py**: Tests the association of videos with specific chat sessions.
- **test_video_functionality.py**: Tests the core video processing functionality.
- **test_video_contextual_memory.py**: Tests the storage of video transcripts and key moments in contextual memory.
- **test_video_immediate_storage.py**: Tests that video information is immediately stored in contextual memory.
- **test_video_folder_storage.py**: Tests the storage of video files in the appropriate folders.

## Integration Tests

Tests that involve multiple components working together.

- **test_app_video_memory.py**: Tests the integration of video memory functionality in the main application.
- **test_conversation_flow.py**: Tests the end-to-end conversation flow including context retrieval.

## Running the Tests

To run a specific test, navigate to the tests directory and run the test script with Python:

```bash
cd tests/api_tests
python test_ollama_api.py
```

Or run a test from the root directory:

```bash
python tests/api_tests/test_ollama_api.py
```

## Adding New Tests

When adding new tests, please follow these guidelines:

1. Place the test in the appropriate category directory
2. Use a descriptive name with the prefix `test_`
3. Include docstrings explaining the purpose of the test
4. Update this README with information about the new test
