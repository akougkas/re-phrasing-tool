"""
Text Humanizer - Main Application Module

This module serves as the entry point for the Text Humanizer application, providing
both chat and text humanization capabilities through a web interface and API.

Key Features:
    - Chat interface with smart chip support
    - Text humanization through @humanize commands
    - Streaming responses for real-time feedback
    - Context-aware processing
    - Configurable model endpoints
"""

import os
from typing import Dict, Any, Generator
import json
from pathlib import Path
from functools import wraps

from flask import Flask, request, jsonify, Response, stream_with_context, render_template
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_compress import Compress

from text_humanizer.providers.local_llm_provider import LocalLLMProvider
from text_humanizer.config.model_config import ModelType
from text_humanizer.chips import ChipDetector, ChipRegistry, HumanizeHandler
from text_humanizer.config.app_config import AppConfig
from text_humanizer.utils.logger import logger
from text_humanizer.user_interface import display_welcome_message, display_typing_indicator, handle_input, clear_chat_history

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = AppConfig()
config_file = Path(__file__).parent / "config" / "config.json"
config.load_config(config_file)

# Configure Flask app
app.config.update(
    SECRET_KEY=config.secret_key,
    WTF_CSRF_ENABLED=config.csrf_enabled
)

# Initialize extensions
csrf = CSRFProtect(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})
compress = Compress(app)

# Initialize models
chat_model = LocalLLMProvider(ModelType.CHAT)
humanizer_model = LocalLLMProvider(ModelType.HUMANIZE)

# Initialize chip system
chip_registry = ChipRegistry()
humanize_handler = HumanizeHandler(humanizer_model)
chip_registry.register(humanize_handler)
chip_detector = ChipDetector(chip_registry)

def stream_response(generator: Generator[str, None, None]) -> Response:
    """Create a streaming response from a generator."""
    return Response(
        stream_with_context(generator),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with smart chip support."""
    if not request.is_json:
        return jsonify({"error": "Invalid content type"}), 400
        
    data = request.get_json()
    message = data.get('message', '').strip()
    stream = data.get('stream', False)
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
        
    try:
        # Check for smart chips
        chip_results = chip_detector.process_chips(message)
        
        if chip_results["chip_results"]:
            # We have processed chips, return their results
            return jsonify({
                "type": "chip_response",
                "text": chip_results["processed_text"],
                "results": chip_results["chip_results"]
            })
        else:
            # Regular chat message
            messages = [{"role": "user", "content": message}]
            
            if stream:
                return stream_response(chat_model.generate(messages, stream=True))
            else:
                response = chat_model.generate(messages, stream=False)
                return jsonify({
                    "type": "chat_response",
                    "text": response.get('content', ''),
                    "role": response.get('role', 'assistant'),
                    "finish_reason": response.get('finish_reason', 'stop')
                })
                
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "error": str(e),
            "type": "error",
            "details": getattr(e, 'details', None)
        }), 500

@app.route('/api/humanize', methods=['POST'])
def humanize():
    """Direct text humanization endpoint."""
    if not request.is_json:
        return jsonify({"error": "Invalid content type"}), 400
        
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        messages = [{"role": "user", "content": text}]
        response = next(humanizer_model.generate(messages))
        return jsonify(json.loads(response))
    except Exception as e:
        logger.error(f"Error humanizing text: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat_interface():
    display_typing_indicator()  # Show typing indicator
    user_input = request.form.get('message')
    handle_input(user_input)  # Handle user input
    # Additional chat processing logic here
    return jsonify({'status': 'success'})

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    clear_chat_history()  # Clear chat history
    return jsonify({'status': 'chat cleared'})

@app.route('/', methods=['GET'])
def index():
    """Main route handling the GET request for the main interface."""
    return render_template('index.html')

@app.route('/', methods=['POST'])
def index_post():
    """Main route handling the POST request for text humanization."""
    # Log request details for debugging
    logger.info(f"Received POST request: Content-Type={request.content_type}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Check if request is JSON
    if not request.is_json:
        logger.error("Request is not JSON")
        return jsonify({"status": "error", "error": "Invalid content type"}), 400

    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        return jsonify({"status": "error", "error": "Invalid JSON data"}), 400

    if not data or not isinstance(data, dict):
        logger.error("Data is not a dictionary")
        return jsonify({"status": "error", "error": "Invalid request format"}), 400

    query = data.get('query', '').strip()
    logger.info(f"Extracted query: '{query}'")

    if not query:
        logger.error("Query is empty")
        return jsonify({"status": "error", "error": "Query text is required"}), 400

    if len(query) < 2:
        logger.error("Query too short")
        return jsonify({"status": "error", "error": "Query must be at least 2 characters long"}), 400

    if len(query) > 1000:
        logger.error("Query too long")
        return jsonify({"status": "error", "error": "Query cannot exceed 1000 characters"}), 400

    try:
        # Get user identifier for rate limiting
        user_id = request.remote_addr or "anonymous"
        logger.info(f"Received query from {user_id}: {query}")
        
        # Process input and merge with context
        messages = [{"role": "user", "content": query}]
        response = next(humanizer_model.generate(messages))
        return jsonify(json.loads(response))
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    display_welcome_message()
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )