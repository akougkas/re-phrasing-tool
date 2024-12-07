"""
Handler for the @humanize smart chip.
"""

from typing import Dict, Any
import json

from text_humanizer.chips.chip_detector import ChipHandler, register_chip_handler
from text_humanizer.providers.local_llm_provider import LocalLLMProvider
from text_humanizer.config.model_config import ModelType
from text_humanizer.utils.logger import logger

@register_chip_handler(
    chip_type="humanize",
    description="Humanize and improve the given text while maintaining its core meaning"
)
class HumanizeHandler(ChipHandler):
    """Handler for text humanization requests."""
    
    def __init__(self, model: LocalLLMProvider):
        """Initialize the handler with a model provider configured for humanization."""
        if not isinstance(model, LocalLLMProvider):
            model = LocalLLMProvider(ModelType.HUMANIZER)
        self.model = model
        
    def handle(self, content: str, parameters: Dict[str, str]) -> Dict[str, Any]:
        """Process a humanization request.
        
        Args:
            content: Text to humanize
            parameters: Optional parameters for customization
                - tone: Desired tone (formal/casual/technical)
                - preserve_format: Whether to maintain text formatting
                
        Returns:
            Dictionary containing:
            - humanized_text: The improved text
            - display_text: Text to show in chat
            - original_text: The input text
            - changes: List of changes made
            - metadata: Additional information
        """
        try:
            # Ensure model is configured for humanization
            if self.model.model_type != ModelType.HUMANIZER:
                self.model.configure(ModelType.HUMANIZER)
            
            # Prepare messages for the model
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            # Generate humanized text
            response_generator = self.model.generate(
                messages,
                stream=False,
                temperature=0.7,  # Balanced creativity
                max_tokens=len(content) * 2  # Reasonable limit
            )
            
            # Get the response (we expect only one yield since stream=False)
            response_json = next(response_generator)
            response_data = json.loads(response_json)
            
            # Create a user-friendly display version
            display_text = (
                "✨ Humanized version:\n"
                f"{response_data['humanized_text']}\n\n"
                "Changes made:\n" +
                "\n".join(f"• {change}" for change in response_data['changes_made'])
            )
            
            return {
                "humanized_text": response_data['humanized_text'],
                "display_text": display_text,
                "original_text": content,
                "changes": response_data['changes_made'],
                "metadata": {
                    "confidence": response_data['confidence_score'],
                    "tone": response_data['tone'],
                    **response_data['metadata']
                }
            }
            
        except Exception as e:
            logger.error(f"Error in humanize handler: {str(e)}")
            raise ValueError(f"Failed to humanize text: {str(e)}")
