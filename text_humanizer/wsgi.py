"""WSGI entry point for the Text Humanizer application."""
import os
from . import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
