"""
Context management system for handling conversation history and context selection using ChromaDB.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import chromadb
from chromadb.config import Settings
import os
import time
import json
from .logger_config import logger
from .error_handling import ContextError, ValidationError
from functools import lru_cache

# Global list to store selected segment IDs
selected_segment_ids = []

@dataclass
class ContextSegment:
    """Represents a segment of conversation context"""
    segment_id: str
    content: str
    role: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

class ContextManager:
    """Manages conversation context using ChromaDB"""
    
    def __init__(self, persist_directory: str = "chroma_db"):
        """Initializes the ContextManager with ChromaDB backend.
        
        Args:
            persist_directory: Directory where ChromaDB will store its data
        
        Raises:
            ContextError: If ChromaDB initialization fails
        """
        self.chat_history = []
        self._selected_segments: List[str] = []
        self._cache = {}  # In-memory cache
        self._cache_ttl = 300  # 5 minutes TTL
        
        try:
            # Initialize ChromaDB client with basic settings
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                    is_persistent=True
                )
            )
            
            # Create or get the collection with basic settings
            self.collection = self.client.get_or_create_collection(
                name="qa_pairs",
                metadata={"description": "Storage for question-answer pairs"}
            )
            
            logger.info("Initialized ChromaDB-backed ContextManager")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise ContextError("Failed to initialize context management system")

    def log_context_operation(self, operation: str, context_id: str):
        logger.info(f"Operation '{operation}' performed on context '{context_id}'")

    def add_message(self, message: str, role: str, question: Optional[str] = None):
        """Adds a new message to the chat history and ChromaDB if it's a QA pair.

        Args:
            message: The message content
            role: The role of the sender ('user' or 'assistant')
            question: The associated question if this is an answer

        Raises:
            ValidationError: If content or role is missing
        """
        if not message or not role:
            raise ValidationError("Content and role are required")
            
        self.chat_history.append({'role': role, 'content': message})
        
        # If this is an answer and we have a question, store the QA pair
        if role == 'assistant' and question:
            segment_id = f"qa_{int(time.time())}"
            try:
                self.collection.add(
                    ids=[segment_id],
                    documents=[message],  # The answer
                    metadatas=[{
                        "question": question,
                        "timestamp": time.time(),
                        "type": "qa_pair"
                    }]
                )
                logger.debug(f"Stored QA pair with ID {segment_id}")
            except Exception as e:
                logger.error(f"Error storing QA pair: {str(e)}")
                raise ContextError("Failed to store QA pair")
        
        logger.debug(f"Added message from {role}: {message[:50]}...")

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the entire chat history."""
        return self.chat_history

    def clear_history(self):
        """Clears the chat history."""
        self.chat_history = []
        logger.info("Chat history cleared")

    def get_selected_context(self) -> List[Tuple[str, str]]:
        """Return currently selected context segments.
        
        Returns:
            List[Tuple[str, str]]: List of selected context segments as tuples
        """
        if not self._selected_segments:
            return []
            
        try:
            results = self.collection.get(
                ids=self._selected_segments,
                include=['metadatas', 'documents']
            )
            
            qa_pairs = []
            for metadata, document in zip(results['metadatas'], results['documents']):
                qa_pairs.append((metadata['question'], document))
                
            logger.info(f"Retrieved {len(qa_pairs)} selected context segments")
            return qa_pairs
        except Exception as e:
            logger.error(f"Error retrieving selected context segments: {str(e)}")
            raise ContextError("Failed to retrieve selected context segments")

    def get_recent_context(self, n: int = 2) -> List[Tuple[str, str]]:
        """Return the most recent Q/A pairs.
        
        Args:
            n: Number of recent Q/A pairs to return
            
        Returns:
            List[Tuple[str, str]]: List of recent Q/A pairs as tuples
        """
        try:
            results = self.collection.query(
                query_texts=[""],  # Empty query to get all results
                n_results=n,
                include=['metadatas', 'documents']
            )
            
            qa_pairs = []
            if results['metadatas']:
                for metadata, document in zip(results['metadatas'][0], results['documents'][0]):
                    qa_pairs.append((metadata['question'], document))
                    
            logger.info(f"Retrieved {len(qa_pairs)} recent Q/A pairs")
            return qa_pairs
        except Exception as e:
            logger.error(f"Error retrieving recent context segments: {str(e)}")
            raise ContextError("Failed to retrieve recent context segments")

    def select_context(self, segment_ids: List[str]) -> bool:
        """Select specific context segments for use.
        
        Args:
            segment_ids: List of segment IDs to select
            
        Returns:
            bool: True if selection was successful
        """
        if not segment_ids:
            raise ValidationError("No segment IDs provided")
        
        try:
            # Verify these IDs exist in ChromaDB
            results = self.collection.get(
                ids=segment_ids,
                include=['metadatas']
            )
            
            if len(results['ids']) == len(segment_ids):
                self._selected_segments = segment_ids
                global selected_segment_ids
                selected_segment_ids = segment_ids
                logger.info(f"Selected {len(segment_ids)} context segments: {segment_ids}")
                for segment_id in segment_ids:
                    self.log_context_operation("select", segment_id)
                return True
            else:
                logger.warning("Some requested segment IDs were not found")
                return False
        except Exception as e:
            logger.error(f"Error selecting context segments: {str(e)}")
            raise ContextError("Failed to select context segments")

    def clear_context(self):
        """Clear all stored context and selections."""
        self.chat_history = []
        self._selected_segments = []
        global selected_segment_ids
        selected_segment_ids = []
        logger.info("Cleared all context and selections")

    def segment_exists(self, segment_id: str) -> bool:
        """Check if a segment exists in the collection.
        
        Args:
            segment_id: ID of the segment to check
            
        Returns:
            bool: True if segment exists, False otherwise
        """
        try:
            results = self.collection.get(
                ids=[segment_id],
                include=['metadatas']
            )
            return len(results['ids']) > 0
        except Exception as e:
            logger.error(f"Error checking segment existence: {str(e)}")
            return False

    def get_all_segments(self) -> List[Dict[str, Any]]:
        """Get all available context segments.
        
        Returns:
            List[Dict[str, Any]]: List of all context segments
        """
        try:
            # Get all items from the collection
            result = self.collection.get()
            segments = []
            
            # If there are no items, return empty list
            if not result or not result['ids']:
                return segments
            
            # Convert ChromaDB results to dictionaries
            for idx, id_ in enumerate(result['ids']):
                metadata = result['metadatas'][idx] if result.get('metadatas') else {}
                content = result['documents'][idx] if result.get('documents') else ""
                segments.append({
                    "id": id_,
                    "content": content,
                    "metadata": metadata
                })
            
            return segments
        except Exception as e:
            logger.error(f"Error retrieving segments: {str(e)}")
            return []

    @lru_cache(maxsize=1000)
    def _get_cached_query(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Cache wrapper for query results."""
        return self._cache.get(query)

    def _set_cache(self, query: str, results: List[Dict[str, Any]]) -> None:
        """Set cache with TTL."""
        self._cache[query] = {
            'data': results,
            'timestamp': time.time()
        }

    def _clean_expired_cache(self) -> None:
        """Clean expired cache entries."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v['timestamp'] > self._cache_ttl
        ]
        for k in expired_keys:
            del self._cache[k]

    def query_context(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query the context with caching."""
        # Clean expired cache entries
        self._clean_expired_cache()
        
        # Check cache first
        cached_result = self._get_cached_query(query)
        if cached_result:
            return cached_result['data']
        
        # If not in cache, query ChromaDB
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Process and cache results
            processed_results = self._process_query_results(results)
            self._set_cache(query, processed_results)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error querying context: {str(e)}")
            raise ContextError(f"Failed to query context: {str(e)}")

    def _process_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process query results into a list of dictionaries."""
        processed_results = []
        for idx, id_ in enumerate(results['ids']):
            metadata = results['metadatas'][idx] if results.get('metadatas') else {}
            content = results['documents'][idx] if results.get('documents') else ""
            distance = results['distances'][idx] if results.get('distances') else 0
            processed_results.append({
                "id": id_,
                "content": content,
                "metadata": metadata,
                "distance": distance
            })
        return processed_results