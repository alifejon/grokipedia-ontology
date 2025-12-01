"""
Utility functions for Grokipedia Ontology.

Provides common utilities for URI sanitization, logging, and error handling.
"""

from __future__ import annotations

import logging
import re
import sys
from functools import lru_cache
from typing import Any


# Configure module logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the given module name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# URI-safe character pattern (alphanumeric, underscore, hyphen)
URI_SAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")


def sanitize_uri_component(value: str) -> str:
    """
    Sanitize a string to be safe for use in URIs.

    Replaces spaces with underscores and removes or encodes
    characters that are not URI-safe.

    Args:
        value: String to sanitize

    Returns:
        URI-safe string

    Examples:
        >>> sanitize_uri_component("Hello World")
        'Hello_World'
        >>> sanitize_uri_component("C++ Programming")
        'Cpp_Programming'
        >>> sanitize_uri_component("Test (Example)")
        'Test_Example'
    """
    if not value:
        return ""

    # Replace common special characters
    result = value.replace(" ", "_")
    result = result.replace("++", "pp")  # C++ -> Cpp
    result = result.replace("#", "Sharp")  # C# -> CSharp
    result = result.replace("&", "And")
    result = result.replace("@", "At")

    # Remove parentheses but keep content
    result = result.replace("(", "_").replace(")", "")
    result = result.replace("[", "_").replace("]", "")
    result = result.replace("{", "_").replace("}", "")

    # Replace other special characters
    result = URI_SAFE_PATTERN.sub("_", result)

    # Clean up multiple underscores
    while "__" in result:
        result = result.replace("__", "_")

    # Remove leading/trailing underscores
    result = result.strip("_")

    return result


def validate_concept_name(name: str) -> bool:
    """
    Validate that a concept name is URI-safe.

    Args:
        name: Concept name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    # Must not start with a number
    if name[0].isdigit():
        return False

    # Check for invalid characters
    return not URI_SAFE_PATTERN.search(name)


class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Base for exponential calculation
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class GrokipediaError(Exception):
    """Base exception for Grokipedia Ontology errors."""
    pass


class FetchError(GrokipediaError):
    """Error during data fetching."""

    def __init__(self, message: str, topic: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.topic = topic
        self.status_code = status_code


class OntologyError(GrokipediaError):
    """Error in ontology operations."""
    pass


class ValidationError(GrokipediaError):
    """Error in data validation."""
    pass


class CyclicReferenceError(OntologyError):
    """Error when cyclic reference is detected in ontology."""

    def __init__(self, message: str, cycle: list[str] | None = None):
        super().__init__(message)
        self.cycle = cycle
