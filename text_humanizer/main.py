"""
Text Humanizer - Main Application Module

This module serves as the entry point for the Text Humanizer application, a Flask-based service
that transforms machine-generated text into more natural, human-like language. It provides
both API endpoints and a web interface for text humanization.

Key Features:
    - RESTful API endpoints for text humanization
    - Context-aware text processing
    - Caching and compression for performance optimization
    - CSRF protection for security
    - Configurable environment-based settings
    - Hot-reloading of configuration in development

Architecture:
    The application follows a modular architecture with the following components:
    - Input Processing: Validates and preprocesses text input
    - Context Management: Handles context storage and retrieval
    - LLM Integration: Interfaces with language models
    - Configuration: Manages environment-specific settings
    - Error Handling: Provides consistent error responses

Usage:
    To run the application:
    1. Set the APP_ENV environment variable (development/production)
    2. Execute this module directly: python3 -m text_humanizer.main
    3. Access the web interface at http://localhost:5000
    4. Use the API endpoints for programmatic access

Dependencies:
    - Flask: Web framework
    - Flask-WTF: CSRF protection
    - Flask-Caching: Response caching
    - Flask-Compress: Response compression
    - ChromaDB: Vector storage for context
"""

"""
Main entry point for the Text Humanizer application.
Provides Flask routes and core application logic for the text humanization service.
"""
import os
from typing import Dict, Any
import logging
import secrets
import re
from functools import wraps
import json
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_caching import Cache
from flask_compress import Compress

from text_humanizer.error_handling import (
    error_handler, TextHumanizerError, ValidationError,
    LLMServiceError, ContextError
)
from text_humanizer.logger_config import logger
from text_humanizer.input_processor import InputProcessor
from text_humanizer.providers.local_llm_provider import LocalLLMProvider
from text_humanizer.context_manager import ContextManager
from text_humanizer.llm_client import LLMClient
from text_humanizer.utils.config import Config

# Get the absolute path to the config directory
current_dir = Path(__file__).parent
config_dir = current_dir / "config"

# Initialize configuration
config = Config(config_dir=str(config_dir), env=os.getenv("APP_ENV", "development"))
config.load_config()

# Enable hot-reloading of config in development
if config.get("debug_mode", False):
    config.start_hot_reload()

# Initialize Flask app with comprehensive configuration
app = Flask(__name__)

# Load app configuration from our config system
app.config['SECRET_KEY'] = config.get('secret_key', secrets.token_hex(32))
app.config['WTF_CSRF_ENABLED'] = config.get('csrf_enabled', True)
app.config['WTF_CSRF_CHECK_DEFAULT'] = config.get('csrf_check_default', False)

# Configure logging with appropriate level based on environment
logging.getLogger().setLevel(config.get('log_level', 'INFO'))

# Cache configuration from config system with performance optimization settings
cache_settings = config.get('cache_settings', {
    'type': 'simple',  # Options: simple, redis, memcached
    'timeout': 300     # Cache timeout in seconds
})
app.config['CACHE_TYPE'] = cache_settings.get('type', 'simple')
app.config['CACHE_DEFAULT_TIMEOUT'] = cache_settings.get('timeout', 300)
cache = Cache(app)

# Enable compression for reduced bandwidth usage
compress = Compress()
compress.init_app(app)

csrf = CSRFProtect(app)

# Initialize core application components with configuration
context_manager = ContextManager(
    persist_directory=config.get('persist_directory', "text_humanizer/data/chroma_db")
)
input_processor = InputProcessor(context_manager=context_manager)

# Initialize providers
model_settings = config.get('model_settings', {})
local_llm_provider = LocalLLMProvider(
    endpoint_url=model_settings.get('endpoint_url'),
    model_name=model_settings.get('model_name'),
    config_name=model_settings.get('config_name', 'default')
)
llm_client = LLMClient()

def handle_json_error(f):
    """
    Decorator for consistent JSON error handling across API endpoints.
    
    Catches exceptions and returns them as JSON responses with appropriate HTTP status codes.
    Ensures consistent error format for API consumers.
    
    Args:
        f: The function to wrap
        
    Returns:
        decorated_function: The wrapped function with error handling
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Error: {str(e)}")
            return jsonify({"status": "error", "error": str(e)}), 400
    return decorated_function

@app.after_request
def after_request(response):
    """
    Post-processing middleware for all responses.
    
    Handles:
        - CSRF token generation for JSON requests
        - Cache control headers
        - Keep-alive connections
        - Response compression (via Flask-Compress)
    
    Args:
        response: Flask response object
        
    Returns:
        response: Modified Flask response object
    """
    if request.is_json:
        csrf_token = generate_csrf()
        response.headers['X-CSRF-Token'] = csrf_token
    
    response.headers['Cache-Control'] = 'public, max-age=300'
    response.headers['Vary'] = 'Accept-Encoding'
    response.headers['Connection'] = 'keep-alive'
    
    return response

@app.route('/process', methods=['POST'])
@handle_json_error
@error_handler
def process_text():
    """
    Processes text with streaming response support.
    Handles the progressive loading of responses.
    
    Returns:
        Response: Streaming response with humanized text
    """
    if not request.is_json:
        return jsonify({"status": "error", "error": "Invalid content type"}), 400

    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"status": "error", "error": "No text provided"}), 400

    def generate():
        try:
            # Process the text in chunks
            response = local_llm_provider.generate_text(
                text,
                stream=True,
                max_tokens=config.get('max_tokens', 1000),
                temperature=config.get('temperature', 0.7)
            )
            
            # Stream each chunk as it's generated
            for chunk in response:
                if isinstance(chunk, dict) and 'content' in chunk:
                    yield chunk['content']
                elif isinstance(chunk, str):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}")
            yield json.dumps({"status": "error", "error": str(e)})

    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8',
            'Transfer-Encoding': 'chunked',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-CSRF-Token'
        }
    )

@app.route('/', methods=['GET'])
@handle_json_error
def index():
    """
    Main route handling the GET request for the main interface.
    
    Returns:
        Rendered template with context
    """
    model_info = f"Connected to model: {local_llm_provider.config.model_name}"
    return render_template('index.html', model_info=model_info)

@app.route('/', methods=['POST'])
@handle_json_error
def index_post():
    """
    Main route handling the POST request for text humanization.
    
    Returns:
        JSON response with humanized text
    """
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
        processed_input = input_processor.process(query, user_id=user_id)
        if not processed_input:
            return jsonify({
                "status": "error",
                "error": "Failed to process input text"
            }), 400
                
        # Get response from LLM
        try:
            response = local_llm_provider.infer(processed_input)
            if not response or not isinstance(response, dict) or 'response' not in response:
                logger.error("Invalid response format from LLM")
                return jsonify({
                    "status": "error",
                    "error": "Invalid response format from LLM service"
                }), 500
        except ConnectionError as e:
            logger.error(f"LLM connection error: {str(e)}")
            return jsonify({
                "status": "error",
                "error": "Could not connect to LLM service. Please try again."
            }), 503
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return jsonify({
                "status": "error",
                "error": f"LLM service error: {str(e)}"
            }), 500
                
        logger.info(f"Generated response: {response}")
        
        return jsonify({
            "status": "success",
            "response": response['response']
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
        
@app.route('/select-context', methods=['POST'])
@handle_json_error
def select_context():
    """
    Updates the selected context segments based on user selection.
    
    Returns:
        Redirects to the index page after updating context.
    """
    segment_id = request.form.get('segment_id')
    if not segment_id:
        raise ValidationError("No segment ID provided")
    
    # Validate segment ID format and existence
    if not isinstance(segment_id, str) or not re.match(r'^[a-zA-Z0-9_-]+$', segment_id):
        raise ValidationError("Invalid segment ID format")
        
    try:
        # Check if segment exists before selecting
        if not context_manager.segment_exists(segment_id):
            raise ValidationError(f"Segment ID {segment_id} not found")
            
        context_manager.select_segment(segment_id)
        logger.info(f"Selected context segment: {segment_id}")
    except Exception as e:
        logger.error(f"Error selecting context: {str(e)}")
        raise ContextError("Failed to select context segment")
        
    return redirect(url_for('index'))

@app.route('/clear-context', methods=['POST'])
@handle_json_error
def clear_context():
    """
    Removes all selected context segments.
    
    Returns:
        Redirects to the index page after clearing context.
    """
    try:
        context_manager.clear_selected_segments()
        logger.info("Cleared all selected context segments")
    except Exception as e:
        logger.error(f"Error clearing context: {str(e)}")
        raise ContextError("Failed to clear context segments")
        
    return redirect(url_for('index'))

@app.route('/update-context', methods=['POST'])
@handle_json_error
def update_context():
    """
    Updates or clears context segments based on form submission.
    Handles both context clearing and segment selection.
    
    Returns:
        Redirects to the index page after updating context.
    """
    action = request.form.get('action')
    if not action:
        raise ValidationError("No action specified")
        
    try:
        if action == 'clear':
            context_manager.clear_selected_segments()
            logger.info("Cleared context segments")
        elif action == 'select':
            segment_ids = request.form.getlist('segment_ids')
            if not segment_ids:
                raise ValidationError("No segments selected")
                
            # Validate each segment ID
            for segment_id in segment_ids:
                if not isinstance(segment_id, str) or not re.match(r'^[a-zA-Z0-9_-]+$', segment_id):
                    raise ValidationError(f"Invalid segment ID format: {segment_id}")
                if not context_manager.segment_exists(segment_id):
                    raise ValidationError(f"Segment ID not found: {segment_id}")
            
            context_manager.select_segments(segment_ids)
            logger.info(f"Updated selected segments: {segment_ids}")
        else:
            raise ValidationError(f"Invalid action: {action}")
    except Exception as e:
        logger.error(f"Error updating context: {str(e)}")
        raise ContextError("Failed to update context")
        
    return redirect(url_for('index'))

if __name__ == "__main__":
    """
    Application entry point.
    
    Loads configuration and starts the Flask development server
    with appropriate host, port, and debug settings.
    """
    host = config.get('host', '127.0.0.1')
    port = config.get('port', 5000)
    debug = config.get('debug_mode', False)
    
    app.run(host=host, port=port, debug=debug)