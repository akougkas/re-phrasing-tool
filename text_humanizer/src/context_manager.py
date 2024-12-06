class ContextManager:
    def __init__(self):
        """Initializes the ContextManager with an empty chat history."""
        self.chat_history = []

    def add_message(self, message, role):
        """Adds a new message to the chat history.

        Args:
            message: The message content.
            role: The role of the sender ('user' or 'assistant').
        """
        self.chat_history.append({'role': role, 'content': message})

    def get_history(self):
        """Returns the entire chat history."""
        return self.chat_history

    def clear_history(self):
        """Clears the chat history."""
        self.chat_history = []