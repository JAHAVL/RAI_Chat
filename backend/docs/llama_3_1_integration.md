# Llama 3.1 Integration Guide

This document provides an overview of the integration of the Llama 3.1 model into the AI Assistant app.

## Overview

The AI Assistant app now supports Meta's Llama 3.1 model for text generation and chat completions. The integration uses the Transformers library to load and run the model.

## Implementation Details

### Meta Llama Handler

The `MetaLlamaHandler` class in `llm/meta_llama_handler.py` has been updated to support Llama 3.1. Key changes include:

- Updated the `_format_messages_for_llama` method to properly format messages for Llama 3.1
- The method now formats system, user, and assistant messages according to Llama 3.1's expected format

### LLM Engine

The `LLMEngine` class in `llm/llm_engine.py` has been updated to use the Meta Llama handler:

- Updated the `_init_meta_llama_model` method to initialize the Meta Llama handler
- Updated the `_meta_llama_generate` method to use the handler for text generation
- Updated the `_meta_llama_chat_completion` method to use the handler for chat completions

## Message Format for Llama 3.1

Llama 3.1 uses a specific format for chat messages:

```
<s>[INST] <<SYS>>
{system_message}
<</SYS>>

{user_message} [/INST] {assistant_message} </s><s>[INST] {next_user_message} [/INST]
```

This format has been implemented in the `_format_messages_for_llama` method.

## Dependencies

The integration requires the following dependencies:

- torch>=2.0.0
- transformers>=4.35.0
- accelerate>=0.25.0

These dependencies are already included in the `requirements.txt` file.

## Testing

A test script has been created at `tests/test_llama_integration.py` to verify the integration. The script tests:

1. The Meta Llama handler directly
2. The LLM engine with the Meta Llama integration

To run the test:

```bash
python tests/test_llama_integration.py --model-path /path/to/llama-3.1-model
```

## Environment Setup

To set up the environment for Llama 3.1:

1. Create a virtual environment:
   ```bash
   python -m venv llama_env
   ```

2. Activate the virtual environment:
   ```bash
   source llama_env/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install torch transformers accelerate numpy==1.24.3
   ```

4. Make sure the Llama 3.1 model is available at the specified path

## Troubleshooting

If you encounter issues with NumPy compatibility, try:

1. Downgrading NumPy to a compatible version:
   ```bash
   pip install numpy==1.24.3
   ```

2. Ensuring that the Python version is compatible with the installed packages

## Next Steps

1. Test the integration with the API endpoints
2. Update the documentation to reflect the new model capabilities
3. Consider adding model configuration options to the app settings
