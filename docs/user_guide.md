# Text Humanizer User Guide

Welcome to Text Humanizer! This guide will help you get started with using our tool to transform machine-generated text into more natural, human-like language.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Tips and Best Practices](#tips-and-best-practices)
5. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

1. Ensure you have Python 3.11 or higher installed
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/re-phrasing-tool.git
   cd re-phrasing-tool
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Copy the example configuration:
   ```bash
   cp text_humanizer/config/config.example.json text_humanizer/config/config.development.json
   ```
2. Edit the configuration file to match your needs:
   ```json
   {
       "debug_mode": true,
       "model_settings": {
           "model_name": "your-preferred-model",
           "temperature": 0.7
       }
   }
   ```

### Starting the Application

1. Set the environment:
   ```bash
   export APP_ENV=development
   ```
2. Start the server:
   ```bash
   python -m text_humanizer.main
   ```
3. Open your browser and navigate to `http://localhost:5000`

## Basic Usage

### Web Interface

1. **Input Text**
   - Enter or paste your text in the input box
   - Optionally provide context for better results
   - Click "Humanize" to process the text

2. **Results**
   - View the humanized text in the output box
   - Compare the original and humanized versions
   - Use the copy button to copy the result

### API Usage

For programmatic access, use our REST API:

```python
import requests

url = "http://localhost:5000/api/humanize"
data = {
    "text": "Your text here",
    "context": "Optional context"
}
response = requests.post(url, json=data)
print(response.json()["humanized_text"])
```

## Advanced Features

### Context Management

Context helps the system better understand your text and produce more appropriate results.

1. **Adding Context**
   - Click "Manage Context"
   - Upload or paste relevant documents
   - Select active context segments

2. **Using Context**
   - Enable "Use Context" when humanizing text
   - Select specific context segments if needed
   - Adjust context relevance settings

### Style Customization

Customize the output style:

1. **Tone Settings**
   - Formal
   - Casual
   - Technical

2. **Length Options**
   - Concise
   - Moderate
   - Detailed

3. **Audience Focus**
   - General
   - Expert
   - Technical

## Tips and Best Practices

### Getting Better Results

1. **Provide Clear Context**
   - Include domain-specific information
   - Specify target audience
   - Mention purpose of the text

2. **Use Appropriate Settings**
   - Match tone to your audience
   - Adjust length based on content type
   - Consider technical level of readers

3. **Iterative Improvement**
   - Start with default settings
   - Adjust based on results
   - Save successful configurations

### Common Use Cases

1. **Technical Documentation**
   ```json
   {
       "style": {
           "tone": "technical",
           "audience": "expert"
       }
   }
   ```

2. **Marketing Content**
   ```json
   {
       "style": {
           "tone": "casual",
           "audience": "general"
       }
   }
   ```

3. **Educational Material**
   ```json
   {
       "style": {
           "tone": "formal",
           "length": "detailed"
       }
   }
   ```

## Troubleshooting

### Common Issues

1. **Poor Quality Output**
   - Check if context is appropriate
   - Verify input text quality
   - Adjust style settings

2. **Performance Issues**
   - Reduce text length
   - Optimize context size
   - Check server resources

3. **Connection Errors**
   - Verify server is running
   - Check network connection
   - Confirm port availability

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid input" | Malformed text | Check input format |
| "Context error" | Missing context | Add required context |
| "Server error" | System issue | Check logs, restart server |

### Getting Help

1. Check the [API Documentation](api.md)
2. Search GitHub issues
3. Contact support team

## Support

Need help? Here's how to get support:

1. **Documentation**
   - Read the [API docs](api.md)
   - Check this user guide
   - Review example code

2. **Community**
   - GitHub Discussions
   - Stack Overflow tags
   - Community forums

3. **Direct Support**
   - Open GitHub issues
   - Email support team
   - Developer Discord
