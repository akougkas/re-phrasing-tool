"""Module for handling input text."""

from context_manager import ContextManager

class InputProcessor:
    """Class for processing input text."""
    

    def read_text_from_file(self, file_path: str) -> str:
        """Reads text from a file and returns it as a string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            return text
        except FileNotFoundError as e:
            print(f"Error: File not found at path: {file_path}")
            print(f"Details: {e}")
            return ""

    def read_text_from_terminal(self) -> str:
        """Reads text input from the terminal, adds it to ContextManager, and returns it."""
        print("Enter text (leave an empty line to finish):")
        context_manager = ContextManager()
        while True:
            line = input()
            if not line:
                break
            context_manager.add_message(role="user", content=line) 
            # Further processing or response generation can be added here
        return context_manager.get_history()  # Or return the last message, etc.

    def handle_multiline_text(self, text: str) -> str:
        """Handles multiline text input."""
        # For now, simply returns the input text.
        # Future enhancements could include parsing and handling line breaks,
        # paragraphs, etc.
        return text