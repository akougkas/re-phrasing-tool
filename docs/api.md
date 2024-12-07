# Text Humanizer API Documentation

This document provides detailed information about the Text Humanizer API endpoints, their usage, and examples.

## Base URL

The base URL for all API endpoints is: `http://your-domain.com/api`

For local development: `http://localhost:5000/api`

## Authentication

The API uses CSRF tokens for security. For JSON requests, the token is returned in the `X-CSRF-Token` header of responses.
Include this token in subsequent requests using the `X-CSRF-Token` header.

## Endpoints

### 1. Humanize Text

Transforms machine-generated text into more natural, human-like language.

**Endpoint:** `POST /humanize`

**Request Headers:**
```
Content-Type: application/json
X-CSRF-Token: your-csrf-token
```

**Request Body:**
```json
{
    "text": "Text to be humanized",
    "context": "Optional context to improve understanding",
    "style": {
        "tone": "casual|formal|technical",
        "length": "concise|moderate|detailed",
        "audience": "general|expert|technical"
    }
}
```

**Response:**
```json
{
    "status": "success",
    "humanized_text": "The transformed, more natural text",
    "confidence_score": 0.95
}
```

**Error Response:**
```json
{
    "status": "error",
    "error": "Description of what went wrong"
}
```

**Status Codes:**
- 200: Success
- 400: Bad Request (invalid input)
- 401: Unauthorized (missing/invalid CSRF token)
- 500: Server Error

### 2. Context Management

#### Get Available Contexts

Retrieves a list of available context segments for text humanization.

**Endpoint:** `GET /context`

**Response:**
```json
{
    "status": "success",
    "contexts": [
        {
            "id": "context-1",
            "description": "Technical documentation context",
            "active": true
        },
        {
            "id": "context-2",
            "description": "Marketing content context",
            "active": false
        }
    ]
}
```

#### Update Context Selection

Updates the active context segments for text humanization.

**Endpoint:** `POST /context`

**Request Body:**
```json
{
    "context_ids": ["context-1", "context-2"]
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Context updated successfully"
}
```

### 3. Health Check

Checks the health status of the API and its dependencies.

**Endpoint:** `GET /health`

**Response:**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "dependencies": {
        "database": "connected",
        "llm_service": "operational"
    }
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- 100 requests per minute per IP address
- 1000 requests per hour per API key

Exceeded limits will return a 429 (Too Many Requests) status code.

## Best Practices

1. **Always include context** when available for better results
2. **Cache responses** when appropriate
3. **Handle errors** gracefully in your application
4. **Use appropriate timeouts** for your HTTP client
5. **Implement exponential backoff** for retries

## Examples

### Python

```python
import requests

def humanize_text(text, context=None):
    url = "http://localhost:5000/api/humanize"
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-Token": "your-csrf-token"
    }
    
    data = {
        "text": text,
        "context": context
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# Example usage
result = humanize_text(
    "The system utilizes advanced algorithms for text processing",
    context="Technical blog post about NLP"
)
print(result["humanized_text"])
```

### JavaScript

```javascript
async function humanizeText(text, context = null) {
    const url = 'http://localhost:5000/api/humanize';
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': 'your-csrf-token'
        },
        body: JSON.stringify({
            text,
            context
        })
    });
    
    return await response.json();
}

// Example usage
humanizeText(
    'The system utilizes advanced algorithms for text processing',
    'Technical blog post about NLP'
).then(result => console.log(result.humanized_text));
```

## Support

For API support, please:

1. Check the documentation first
2. Search existing issues in the GitHub repository
3. Open a new issue if needed

## Changelog

### v1.0.0 (2024-12-07)
- Initial API release
- Basic text humanization
- Context management
- Health check endpoint
