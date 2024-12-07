"""
Main entry point for the Text Humanizer application.
Provides Flask routes and core application logic for the text humanization service.
"""
import os
from typing import Dict, Any
import logging

from flask import Flask, render_template, request, redirect, url_for

from .logger_config import logger
from .input_processor import InputProcessor
from .providers.local_llm_provider import LocalLLMProvider
from .context_manager import ContextManager
from .quality_control import pre_inference_check, validate

app = Flask(__name__)
context_manager = ContextManager()
input_processor = InputProcessor(context_manager=context_manager)
local_llm_provider = LocalLLMProvider()

class TextHumanizerError(Exception):
    """Base exception for Text Humanizer application."""
    pass

class LLMServiceError(TextHumanizerError):
    """Exception raised when LLM service fails."""
    pass

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route handling both GET and POST requests.
    GET: Displays the main interface.
    POST: Processes text humanization requests.
    
    Returns:
        Rendered template with humanized text response and context information.
    """
    response = None
    query = None
    model_info = f"Connected to model: {local_llm_provider.config.model_name}"
    
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            logger.info(f"Received query: {query}")
            logger.info(f"Current selected context segments: {context_manager._selected_segments}")
            
            try:
                # Process input and merge with context
                logger.debug("Processing input...")
                processed_input = input_processor.process(query)
                
                # Validate input
                enhanced_input = pre_inference_check(processed_input)
                logger.debug(f"Enhanced input prepared")
                
                try:
                    # Get LLM response
                    logger.info("Sending request to LLM...")
                    llm_response = local_llm_provider.infer(enhanced_input)
                    validated_response = validate(llm_response)
                    response = validated_response.get('response', 'No response received')
                    logger.info(f"Successfully generated response (length: {len(response)})")
                    logger.debug(f"Generated response preview: {str(response)[:200]}")
                except Exception as e:
                    logger.error(f"LLM service error: {str(e)}", exc_info=True)
                    raise LLMServiceError("The language model service is currently unavailable. Please try again later.")
            except LLMServiceError as e:
                response = str(e)
                logger.error(f"LLM service error shown to user: {response}")
            except Exception as e:
                response = "An unexpected error occurred. Please try again later."
                logger.error(f"Unexpected error during query processing: {str(e)}", exc_info=True)

    context_segments = [qa['question'] for qa in context_manager._mock_qa_pairs]
    return render_template('index.html', 
                         context_segments=context_segments,
                         selected_segment_ids=context_manager._selected_segments,
                         response=response,
                         query=query,
                         model_info=model_info)

@app.route('/select_context', methods=['POST'])
def select_context():
    """
    Updates the selected context segments based on user selection.
    
    Returns:
        Redirects to the index page after updating context.
    """
    selected_context_ids = request.form.getlist('selected_segments')
    logger.info(f"Updating selected context segments: {selected_context_ids}")
    context_manager.select_context(selected_context_ids)
    return redirect(url_for('index'))

@app.route('/clear_context', methods=['POST'])
def clear_context():
    """
    Removes all selected context segments.
    
    Returns:
        Redirects to the index page after clearing context.
    """
    logger.info("Clearing all context segments")
    context_manager.clear_context()
    return redirect(url_for('index'))

@app.route('/update_context', methods=['POST'])
def update_context():
    """
    Updates or clears context segments based on form submission.
    Handles both context clearing and segment selection.
    
    Returns:
        Redirects to the index page after updating context.
    """
    if 'clear_context' in request.form:
        logger.info("Clearing context via update_context endpoint")
        context_manager._selected_segments.clear()
    else:
        selected_segments = request.form.getlist('selected_segments')
        logger.info(f"Updating context segments to: {selected_segments}")
        context_manager._selected_segments.clear()
        context_manager._selected_segments.extend(int(id_) for id_ in selected_segments)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)