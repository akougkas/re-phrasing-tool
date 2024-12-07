"""Views for the main blueprint."""
import re
from flask import render_template, request, redirect, url_for, current_app, g, jsonify
from ...error_handling import error_handler, ValidationError, LLMServiceError
from ...logger_config import logger
from . import bp

@bp.before_request
def before_request():
    """Setup resources needed for each request."""
    g.context_manager = current_app.context_manager
    g.input_processor = current_app.input_processor
    g.local_llm_provider = current_app.local_llm_provider

@bp.route('/', methods=['GET', 'POST'])
@error_handler
def index():
    """Main route handling both GET and POST requests."""
    response = None
    query = None
    model_info = f"Connected to model: {g.local_llm_provider.config.model_name}"
    
    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            raise ValidationError("Query text is required")
            
        user_id = request.remote_addr or "anonymous"
        logger.info(f"Received query from {user_id}: {query}")
        logger.info(f"Current selected context segments: {g.context_manager._selected_segments}")
        
        try:
            processed_input = g.input_processor.process(query, user_id=user_id)
            if not processed_input:
                raise ValidationError("Failed to process input text")
                
            llm_response = g.local_llm_provider.infer(processed_input)
            if not llm_response or llm_response.get("status") == "error":
                error_msg = llm_response.get("response") if llm_response else "Failed to get response from LLM service"
                raise LLMServiceError(error_msg)
                
            logger.info(f"Generated response: {llm_response}")
            
            # Return JSON response for POST requests
            return {"status": "success", "response": llm_response["response"]}
            
        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise LLMServiceError("Failed to process text humanization request")
    
    # Return HTML template for GET requests
    return render_template('index.html',
                         response=response,
                         query=query,
                         model_info=model_info,
                         context_segments=g.context_manager.get_all_segments(),
                         selected_segments=g.context_manager._selected_segments)

@bp.route('/select-context', methods=['POST'])
@error_handler
def select_context():
    """Updates the selected context segments."""
    segment_id = request.form.get('segment_id')
    if not segment_id:
        raise ValidationError("No segment ID provided")
    
    if not isinstance(segment_id, str) or not re.match(r'^[a-zA-Z0-9_-]+$', segment_id):
        raise ValidationError("Invalid segment ID format")
        
    try:
        if not g.context_manager.segment_exists(segment_id):
            raise ValidationError(f"Segment ID {segment_id} not found")
            
        g.context_manager.select_context([segment_id])
        logger.info(f"Selected context segment: {segment_id}")
    except Exception as e:
        logger.error(f"Error selecting context: {str(e)}")
        raise ValidationError(f"Failed to select context: {str(e)}")
    
    return redirect(url_for('main.index'))

@bp.route('/clear-context', methods=['POST'])
@error_handler
def clear_context():
    """Removes all selected context segments."""
    try:
        g.context_manager.clear_context()
        logger.info("Cleared all selected context segments")
    except Exception as e:
        logger.error(f"Error clearing context: {str(e)}")
        raise ValidationError(f"Failed to clear context: {str(e)}")
    
    return redirect(url_for('main.index'))
