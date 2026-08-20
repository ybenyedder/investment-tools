#!/bin/bash
set -e

echo "Installing optional libraries for the EMBEDDED local LLM fallback..."
echo "(In Docker, the dedicated 'llamacpp' service serves the model over HTTP:"
echo " this script is only needed for local dev without that service.)"
pip install llama-cpp-python huggingface-hub bleach pydantic

echo "Downloading TinyLlama-1.1B (Q4_K_M GGUF format, ~680MB)..."
mkdir -p models
hf download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --local-dir models

echo "Installation complete! The local LLM is ready."
