"""
Text Humanizer application factory module.
"""
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_session import Session

from .config import config
from .context_manager import ContextManager
from .input_processor import InputProcessor
from .providers.local_llm_provider import LocalLLMProvider
from .error_handling import register_error_handlers

csrf = CSRFProtect()
session = Session()

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    csrf.init_app(app)
    session.init_app(app)
    
    # Initialize application components
    app.context_manager = ContextManager(persist_directory=app.config['CHROMA_PERSIST_DIRECTORY'])
    app.input_processor = InputProcessor(context_manager=app.context_manager)
    app.local_llm_provider = LocalLLMProvider()
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    from .blueprints.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app