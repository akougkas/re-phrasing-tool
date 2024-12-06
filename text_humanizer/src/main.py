"""
Main entry point for the Text Humanizer application.
"""

from text_humanizer.src.context_manager import ContextManager
from text_humanizer.src.user_interface import ChatGUI
from text_humanizer.src.input_processor import LLMCommunicator  # Renamed for clarity
import queue


def main():
    """
    Initializes and runs the Text Humanizer application.
    """
    # Initialize components
    message_queue = queue.Queue()
    context_manager = ContextManager() 
    llm_communicator = LLMCommunicator(context_manager, message_queue) 
    user_interface = ChatGUI(message_queue, llm_communicator)

    # Connect UI callbacks
    user_interface.set_send_callback(llm_communicator.send_message)
    user_interface.set_clear_chat_callback(user_interface.clear_chat_history)
    user_interface.set_clear_context_callback(context_manager.clear_context)

    # Error handling example (can be expanded)
    def handle_llm_error(error):
        user_interface.display_message("Error: " + str(error), "system")

    llm_communicator.set_error_callback(handle_llm_error)

    # Start the GUI event loop
    try:
        user_interface.run()  
    except KeyboardInterrupt:
        print("Exiting application...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Perform any necessary cleanup here (e.g., closing database connections)
        context_manager.close()  # Example cleanup


def clear_chat_history():
    """Clears the chat history."""
    # Implementation for clearing chat history (e.g., from the GUI and context manager)
    pass


if __name__ == "__main__":
    main()