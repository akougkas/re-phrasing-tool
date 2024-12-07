"""
Tests for smart chip detection and handling.
"""

import pytest
from unittest.mock import Mock, patch

from text_humanizer.chips import ChipDetector, ChipRegistry, HumanizeHandler
from text_humanizer.models import HumanizerModel, ModelConfig

def test_chip_detection():
    """Test basic chip detection."""
    registry = ChipRegistry()
    detector = ChipDetector(registry)
    
    text = "Hello @humanize[tone=formal]{Please improve this text.} Thanks!"
    matches = detector.find_chips(text)
    
    assert len(matches) == 1
    match = matches[0]
    assert match.chip_type == "humanize"
    assert match.content == "Please improve this text."
    assert match.parameters == {"tone": "formal"}

def test_humanize_handler():
    """Test humanize handler functionality."""
    # Mock the model response
    mock_response = {
        "humanized_text": "Improved text version",
        "changes_made": ["Made it clearer"],
        "confidence_score": 0.9,
        "tone": "formal",
        "metadata": {}
    }
    
    # Create mock model
    mock_model = Mock(spec=HumanizerModel)
    mock_model.generate.return_value = iter([mock_response])
    
    # Create handler with mock model
    handler = HumanizeHandler(mock_model)
    
    # Test handling
    result = handler.handle("Test text", {"tone": "formal"})
    
    assert "humanized_text" in result
    assert "display_text" in result
    assert "changes" in result
    assert result["humanized_text"] == "Improved text version"

def test_chip_processing():
    """Test end-to-end chip processing."""
    # Setup
    registry = ChipRegistry()
    mock_model = Mock(spec=HumanizerModel)
    mock_model.generate.return_value = iter([{
        "humanized_text": "Improved version",
        "changes_made": ["Enhanced clarity"],
        "confidence_score": 0.9,
        "tone": "formal",
        "metadata": {}
    }])
    
    handler = HumanizeHandler(mock_model)
    registry.register(handler)
    
    detector = ChipDetector(registry)
    
    # Test
    text = "Start @humanize{Make this better.} End"
    result = detector.process_chips(text)
    
    assert "processed_text" in result
    assert "chip_results" in result
    assert len(result["chip_results"]) == 1
    assert result["chip_results"][0]["success"] is True

def test_invalid_chip():
    """Test handling of invalid chips."""
    registry = ChipRegistry()
    detector = ChipDetector(registry)
    
    text = "@invalid{This should fail}"
    result = detector.process_chips(text)
    
    assert len(result["chip_results"]) == 1
    assert result["chip_results"][0]["success"] is False
    assert "Handler not found" in result["chip_results"][0]["error"]
