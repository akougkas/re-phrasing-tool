"""Main blueprint for the Text Humanizer application."""
from flask import Blueprint

bp = Blueprint('main', __name__)

from . import views  # noqa
