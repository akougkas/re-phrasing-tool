"""Module for handling input text and context processing."""

from typing import Dict, Any, List, Optional, Tuple, Union, Generator
import json
import yaml
import csv
import markdown
from io import StringIO
from pathlib import Path
from datetime import datetime
import logging
import re
import html
import unicodedata
import mimetypes
import hashlib
import time
from text_humanizer.logger_config import logger
from text_humanizer.error_handling import ValidationError, FormatError
from text_humanizer.context_manager import ContextManager
from text_humanizer.utils.validation import InputValidator

class InputProcessor:
    """Class for processing input text and managing context."""
    
    # Constants for validation
    MIN_QUERY_LENGTH = 1
    MAX_QUERY_LENGTH = 2000
    
    # Supported formats
    SUPPORTED_FORMATS = {
        'plain': ['txt', 'text'],
        'json': ['json'],
        'yaml': ['yml', 'yaml'],
        'markdown': ['md', 'markdown'],
        'csv': ['csv'],
    }
    
    def __init__(self, context_manager: Optional[ContextManager] = None):
        """Initialize with optional context manager."""
        self.context_manager = context_manager or ContextManager()
        self._request_counts = {}  # For rate limiting
        self.validator = InputValidator()
        # Format detection cache
        self._format_cache = {}
        self._format_cache_max_size = 1000  # Maximum number of cache entries
        self._format_cache_ttl = 3600  # Cache TTL in seconds
        
    def _validate_input_length(self, text: str) -> None:
        """Validate input length."""
        self.validator.validate_length(text, self.MIN_QUERY_LENGTH, self.MAX_QUERY_LENGTH)
    
    def _validate_input_chars(self, text: str) -> None:
        """Validate input characters."""
        dangerous_chars = set('<>{}[]\\')
        self.validator.validate_characters(text, disallowed_chars=dangerous_chars)
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text."""
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        # Escape HTML entities
        text = html.escape(text)
        # Remove any remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _check_rate_limit(self, user_id: str, max_requests: int = 10, window_seconds: int = 60) -> None:
        """Check rate limit for user."""
        current_time = datetime.now().timestamp()
        user_requests = self._request_counts.get(user_id, [])
        
        # Use the validator for rate limiting
        self.validator.validate_rate_limit(
            request_times=user_requests,
            max_requests=max_requests,
            window_seconds=window_seconds,
            current_time=current_time
        )
        
        # Update request count
        user_requests.append(current_time)
        self._request_counts[user_id] = user_requests

    def _get_format_cache_key(self, content: str, file_extension: Optional[str] = None) -> str:
        """Generate a cache key for format detection."""
        # Use first 100 chars of content + extension for cache key
        content_hash = hashlib.md5(content[:100].encode()).hexdigest()
        return f"{content_hash}_{file_extension or 'no_ext'}"

    def _clean_format_cache(self):
        """Clean expired and excess cache entries."""
        current_time = time.time()
        # Remove expired entries
        expired_keys = [
            k for k, (_, timestamp) in self._format_cache.items()
            if current_time - timestamp > self._format_cache_ttl
        ]
        for k in expired_keys:
            del self._format_cache[k]
        
        # If still too many entries, remove oldest
        if len(self._format_cache) > self._format_cache_max_size:
            sorted_items = sorted(
                self._format_cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            excess_count = len(self._format_cache) - self._format_cache_max_size
            for k, _ in sorted_items[:excess_count]:
                del self._format_cache[k]

    def detect_format(self, content: str, file_extension: Optional[str] = None) -> str:
        """
        Detect the format of the input content with caching.
        
        Args:
            content: The input content to analyze
            file_extension: Optional file extension hint
            
        Returns:
            str: Detected format ('plain', 'json', 'yaml', 'markdown', 'csv')
        """
        # Try cache first
        cache_key = self._get_format_cache_key(content, file_extension)
        if cache_key in self._format_cache:
            format_type, _ = self._format_cache[cache_key]
            return format_type
        
        # Clean cache periodically
        self._clean_format_cache()
        
        # Detect format
        if file_extension:
            ext = file_extension.lower().lstrip('.')
            for format_type, extensions in self.SUPPORTED_FORMATS.items():
                if ext in extensions:
                    # Cache the result
                    self._format_cache[cache_key] = (format_type, time.time())
                    return format_type
        
        # Content-based detection
        content = content.strip()
        detected_format = 'plain'  # Default format
        
        # Check JSON
        try:
            json.loads(content)
            detected_format = 'json'
        except json.JSONDecodeError:
            # Check YAML
            try:
                yaml.safe_load(content)
                if re.match(r'^(-|\s*[a-zA-Z]+\s*:)', content):
                    detected_format = 'yaml'
            except yaml.YAMLError:
                # Check Markdown
                if (re.search(r'^#+\s', content, re.MULTILINE) or  # Headers
                    re.search(r'\[.*\]\(.*\)', content) or         # Links
                    re.search(r'^[-*+]\s', content, re.MULTILINE)  # Lists
                   ):
                    detected_format = 'markdown'
                else:
                    # Check CSV
                    try:
                        dialect = csv.Sniffer().sniff(content)
                        detected_format = 'csv'
                    except csv.Error:
                        pass
        
        # Cache the result
        self._format_cache[cache_key] = (detected_format, time.time())
        return detected_format

    def parse_format(self, content: str, format_type: str) -> Union[str, List[str]]:
        """
        Parse content based on its format.
        
        Args:
            content: The content to parse
            format_type: The format type to parse as
            
        Returns:
            Union[str, List[str]]: Parsed content
            
        Raises:
            FormatError: If parsing fails
        """
        try:
            if format_type == 'json':
                parsed = json.loads(content)
                return json.dumps(parsed, indent=2)
            
            elif format_type == 'yaml':
                parsed = yaml.safe_load(content)
                return yaml.dump(parsed, default_flow_style=False)
            
            elif format_type == 'markdown':
                # Convert markdown to plain text while preserving structure
                html_content = markdown.markdown(content)
                # Remove HTML tags but preserve line breaks
                text = re.sub('<br\s*/?>', '\n', html_content)
                text = re.sub('<[^>]+>', '', text)
                return text
            
            elif format_type == 'csv':
                rows = []
                csv_reader = csv.reader(StringIO(content))
                for row in csv_reader:
                    rows.append(' | '.join(row))
                return '\n'.join(rows)
            
            else:  # plain text
                return content
                
        except Exception as e:
            raise FormatError(
                f"Failed to parse content as {format_type}",
                details={"error": str(e)}
            )

    def process_file(self, file_path: str) -> Tuple[str, str]:
        """
        Process a file with comprehensive error handling and format detection.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Tuple[str, str]: (content, format_type)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If file is too large or content is invalid
            FormatError: If format is unsupported or content is malformed
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size (limit to 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValidationError(
                "File too large",
                details={
                    "max_size": MAX_FILE_SIZE,
                    "file_size": path.stat().st_size
                }
            )
        
        # Try UTF-8 first
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings
            encodings = ['latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    content = path.read_text(encoding=encoding)
                    logger.warning(f"File decoded using fallback encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValidationError(
                    "Unable to decode file content",
                    details={"tried_encodings": ['utf-8'] + encodings}
                )
        
        # Detect format
        format_type = self.detect_format(content, path.suffix)
        
        # Validate content structure based on format
        try:
            if format_type == 'json':
                # Check JSON structure and depth
                def check_json_depth(obj, current_depth=0, max_depth=20):
                    if current_depth > max_depth:
                        raise ValidationError("JSON structure too deep", details={"max_depth": max_depth})
                    if isinstance(obj, dict):
                        for value in obj.values():
                            check_json_depth(value, current_depth + 1, max_depth)
                    elif isinstance(obj, list):
                        for item in obj:
                            check_json_depth(item, current_depth + 1, max_depth)
                
                parsed_json = json.loads(content)
                check_json_depth(parsed_json)
                
            elif format_type == 'yaml':
                # Check YAML structure
                yaml.safe_load(content)  # This will validate YAML structure
                
            elif format_type == 'csv':
                # Validate CSV structure
                csv_reader = csv.reader(StringIO(content))
                row_count = 0
                for row in csv_reader:
                    row_count += 1
                    if row_count > 10000:  # Limit number of rows
                        raise ValidationError(
                            "CSV file too large",
                            details={"max_rows": 10000}
                        )
        
        except (json.JSONDecodeError, yaml.YAMLError, csv.Error) as e:
            raise FormatError(
                f"Invalid {format_type} format",
                details={"error": str(e)}
            )
        
        return content, format_type

    def process_file_streaming(self, file_path: str, chunk_size: int = 8192) -> Generator[str, None, Tuple[str, str]]:
        """
        Process a file using streaming for memory efficiency.
        
        Args:
            file_path: Path to the file to process
            chunk_size: Size of chunks to read at a time
            
        Yields:
            str: Content chunks as they are read
            
        Returns:
            Tuple[str, str]: Final (content, format_type) after processing
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If file is too large or content is invalid
            FormatError: If format is unsupported or content is malformed
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValidationError(
                "File too large",
                details={
                    "max_size": MAX_FILE_SIZE,
                    "file_size": path.stat().st_size
                }
            )
        
        # Initialize variables for streaming
        content_chunks = []
        format_type = None
        encoding = 'utf-8'
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        current_encoding_index = 0
        
        while True:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    # Read initial chunk for format detection
                    initial_chunk = file.read(chunk_size)
                    if not initial_chunk:
                        break
                    
                    # Detect format from initial chunk
                    format_type = self.detect_format(initial_chunk, path.suffix)
                    content_chunks.append(initial_chunk)
                    yield initial_chunk
                    
                    # Stream the rest of the file
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        content_chunks.append(chunk)
                        yield chunk
                    
                    break  # Successfully read the file
                    
            except UnicodeDecodeError:
                # Try next encoding
                current_encoding_index += 1
                if current_encoding_index >= len(encodings_to_try):
                    raise ValidationError(
                        "Unable to decode file content",
                        details={"tried_encodings": encodings_to_try}
                    )
                encoding = encodings_to_try[current_encoding_index]
                content_chunks = []  # Reset chunks for retry
                logger.warning(f"Retrying with encoding: {encoding}")
        
        # Combine chunks and validate content
        content = ''.join(content_chunks)
        
        # Validate content structure based on format
        try:
            if format_type == 'json':
                # Check JSON structure and depth
                def check_json_depth(obj, current_depth=0, max_depth=20):
                    if current_depth > max_depth:
                        raise ValidationError("JSON structure too deep", details={"max_depth": max_depth})
                    if isinstance(obj, dict):
                        for value in obj.values():
                            check_json_depth(value, current_depth + 1, max_depth)
                    elif isinstance(obj, list):
                        for item in obj:
                            check_json_depth(item, current_depth + 1, max_depth)
                
                parsed_json = json.loads(content)
                check_json_depth(parsed_json)
                
            elif format_type == 'yaml':
                # Check YAML structure
                yaml.safe_load(content)
                
            elif format_type == 'csv':
                # Validate CSV structure
                csv_reader = csv.reader(StringIO(content))
                row_count = 0
                for row in csv_reader:
                    row_count += 1
                    if row_count > 10000:
                        raise ValidationError(
                            "CSV file too large",
                            details={"max_rows": 10000}
                        )
        
        except (json.JSONDecodeError, yaml.YAMLError, csv.Error) as e:
            raise FormatError(
                f"Invalid {format_type} format",
                details={"error": str(e)}
            )
        
        return content, format_type

    def process(self, query_string: str, user_id: str = "anonymous", format_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a query string by combining it with relevant context.
        
        Args:
            query_string: The user's query to process
            user_id: Identifier for rate limiting
            format_type: Optional format type override
            
        Returns:
            Dict[str, Any]: Structured input containing query, context, and metadata
            
        Raises:
            ValidationError: If input validation fails
            FormatError: If format processing fails
        """
        # Check rate limit
        self._check_rate_limit(user_id)
        
        # Detect and parse format if not specified
        if not format_type:
            format_type = self.detect_format(query_string)
        
        try:
            # Parse the content based on detected format
            parsed_content = self.parse_format(query_string, format_type)
            
            # Validate parsed content
            self._validate_input_length(parsed_content)
            self._validate_input_chars(parsed_content)
            
            # Sanitize input
            sanitized_content = self._sanitize_input(parsed_content)
            
            # Get context (rest of the method remains the same)
            selected_context = self.context_manager.get_selected_context()
            if not selected_context:
                logging.info("No context explicitly selected, falling back to recent context")
                recent_qa = self.context_manager.get_recent_context(n=2)
                context_list = [
                    f"Q: {qa[0]} A: {qa[1]}"
                    for qa in recent_qa
                ]
            else:
                context_list = [
                    f"Q: {segment[0]} A: {segment[1]}"
                    for segment in selected_context
                ]
            
            # Build the structured input
            structured_input = {
                "query": sanitized_content,
                "prompt": query_string,  # Original query for reference
                "system_prompt": (
                    "You are a helpful assistant specializing in text humanization. Your task is to rephrase and improve text "
                    "while maintaining its core meaning. Make the text more natural, clear, and engaging while preserving the "
                    "original intent. If the input is unclear or ambiguous, ask for clarification. Focus on:"
                    "\n1. Natural flow and readability"
                    "\n2. Clear and concise expression"
                    "\n3. Proper grammar and punctuation"
                    "\n4. Engaging and professional tone"
                    "\nIf you're not sure about something, say so directly."
                ),
                "context": context_list,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "format": format_type,
                    "validation_status": "passed"
                }
            }
            
            # Debug output
            logging.debug("Processed input structure:")
            logging.debug(f"Merged Input: {structured_input}")
            
            return structured_input
            
        except (FormatError, ValidationError) as e:
            logging.error(f"Error processing input: {str(e)}")
            raise

    def format_debug_output(self, structured_input: Dict[str, Any]) -> str:
        """
        Format the structured input for debug display.
        
        Args:
            structured_input: The processed input structure
            
        Returns:
            str: Formatted debug string
        """
        return json.dumps(structured_input, indent=2)

    def handle_multiline_text(self, text: str) -> str:
        """
        Handle multiline text with proper paragraph and line break processing.
        
        Args:
            text: The multiline text to process
            
        Returns:
            str: Processed text with normalized paragraphs and line breaks
            
        This method:
        1. Preserves intentional line breaks (paragraphs)
        2. Normalizes whitespace within paragraphs
        3. Maintains list formatting and indentation
        4. Preserves code blocks and preformatted text
        """
        # Handle code blocks (preserve formatting)
        code_blocks = {}
        code_block_pattern = r'```[\s\S]*?```|`[^`]+`'
        
        def save_code_block(match):
            placeholder = f'__CODE_BLOCK_{len(code_blocks)}__'
            code_blocks[placeholder] = match.group(0)
            return placeholder
        
        # Save code blocks
        text_with_placeholders = re.sub(code_block_pattern, save_code_block, text)
        
        # Split into paragraphs (preserve intentional line breaks)
        paragraphs = text_with_placeholders.split('\n\n')
        
        # Process each paragraph
        processed_paragraphs = []
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
                
            # Preserve list formatting
            if re.match(r'^[\s]*[-*+]\s', paragraph):
                # Handle list items
                lines = paragraph.split('\n')
                processed_lines = [' '.join(line.split()) for line in lines]
                processed_paragraphs.append('\n'.join(processed_lines))
            else:
                # Normal paragraph - normalize whitespace
                processed_paragraphs.append(' '.join(paragraph.split()))
        
        # Rejoin paragraphs
        processed_text = '\n\n'.join(processed_paragraphs)
        
        # Restore code blocks
        for placeholder, code_block in code_blocks.items():
            processed_text = processed_text.replace(placeholder, code_block)
        
        return processed_text