"""
User interface module for handling user interactions and displaying responses.
"""

def display_response(final_response):
    """
    Displays the final response to the user.
    Currently just prints the response.
    
    Args:
        final_response: The processed response to display
    """
    print("Response:", final_response)

def show_context_selector(context_segments):
    """
    Shows the context selector interface with available segments.
    Currently just prints the segments.
    
    Args:
        context_segments: List of context segments to display
    """
    print("Available context segments:")
    for i, segment in enumerate(context_segments):
        print(f"{i + 1}. {segment}")

def onClearChat():
    """
    Handler for clearing the chat history.
    Currently just prints the action.
    """
    print("Action: Clearing chat history")

def onClearContext():
    """
    Handler for clearing the context.
    Currently just prints the action.
    """
    print("Action: Clearing context")

def onSelectContext():
    """
    Handler for context selection.
    Currently just prints the action.
    """
    print("Action: Selecting context")

def render_context_options(context_segments):
    """
    Renders a numbered list of available context segments and simulates user selection.
    
    Args:
        context_segments: List of context segments to display
    """
    print("Select from the following context segments:")
    for i, segment in enumerate(context_segments):
        print(f"{i + 1}. {segment}")
    
    # Simulate user selection by hardcoding some IDs
    selected_ids = ['qa1', 'qa3']
    print(f"Simulated selection: {selected_ids}")
    return selected_ids

def display_typing_indicator():
    """
    Displays a typing indicator to simulate the model thinking or typing.
    """
    print("The model is typing...")


def send_message(message):
    """
    Sends the message when Enter is pressed.
    """
    print("Message sent:", message)


def handle_input(input_text):
    """
    Handles input text, sending the message or creating a new line.
    """
    if input_text.endswith("\n"):
        send_message(input_text.strip())
    else:
        print("New line added")


def display_welcome_message():
    """
    Displays a welcome message with LLM provider and active model information.
    """
    print("Welcome to the chat! LLM Provider: OpenAI, Available Models: GPT-3, GPT-4, Active Model: GPT-4")


def clear_chat_history():
    """
    Clears the chat history.
    """
    print("Chat history cleared")


# Example usage
if __name__ == "__main__":
    display_welcome_message()
    display_typing_indicator()  # Simulate typing indicator
    handle_input("Hello, how are you?\n")  # Simulate sending a message
    clear_chat_history()  # Simulate clearing chat history