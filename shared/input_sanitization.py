"""Input Sanitization Module for Prompt Injection Protection.

This module provides utilities to detect and prevent prompt injection attacks
by filtering dangerous patterns from user input before it reaches the LLM.

Common attack patterns blocked:
- Role switching attempts ("ignore previous instructions", "you are now...")
- System prompt override attempts ("system:", "[INST]", etc.)
- Delimiter injection (attempting to break out of user message context)
- Jailbreak patterns ("DAN mode", "developer mode", etc.)

Usage:
    from shared.input_sanitization import sanitize_user_input, InputSanitizationError

    try:
        clean_input = sanitize_user_input(user_prompt)
    except InputSanitizationError as e:
        # Handle blocked input
        print(f"Blocked: {e}")
"""

from __future__ import annotations

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class InputSanitizationError(ValueError):
    """Raised when user input contains potentially malicious content."""
    
    def __init__(self, message: str, pattern_matched: str = ""):
        super().__init__(message)
        self.pattern_matched = pattern_matched


# Dangerous patterns that indicate prompt injection attempts
# Each tuple: (compiled_regex, description, severity)
# Severity: "block" = reject entirely, "warn" = log but allow (future use)
DANGEROUS_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # Role switching / instruction override
    (
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)", re.IGNORECASE),
        "Instruction override attempt",
        "block"
    ),
    (
        re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", re.IGNORECASE),
        "Instruction override attempt",
        "block"
    ),
    (
        re.compile(r"forget\s+(everything|all|your)\s+(you|instructions?|rules?)", re.IGNORECASE),
        "Instruction override attempt",
        "block"
    ),
    (
        re.compile(r"you\s+are\s+now\s+(a|an|the)?\s*(new|different|evil|unrestricted)", re.IGNORECASE),
        "Role switching attempt",
        "block"
    ),
    (
        re.compile(r"pretend\s+(you\s+are|to\s+be)\s+(a|an)?\s*(different|new|evil|unrestricted)", re.IGNORECASE),
        "Role switching attempt",
        "block"
    ),
    (
        re.compile(r"act\s+as\s+(if\s+)?(you\s+are\s+)?(a|an)?\s*(different|unrestricted|evil)", re.IGNORECASE),
        "Role switching attempt",
        "block"
    ),
    
    # System prompt markers (attempting to inject system-level instructions)
    (
        re.compile(r"^\s*system\s*:", re.IGNORECASE | re.MULTILINE),
        "System prompt injection",
        "block"
    ),
    (
        re.compile(r"\[INST\]|\[/INST\]|\[\[SYSTEM\]\]", re.IGNORECASE),
        "Instruction delimiter injection",
        "block"
    ),
    (
        re.compile(r"<\|system\|>|<\|user\|>|<\|assistant\|>", re.IGNORECASE),
        "Chat template injection",
        "block"
    ),
    (
        re.compile(r"###\s*(System|Human|Assistant)\s*:", re.IGNORECASE),
        "Markdown role injection",
        "block"
    ),
    
    # Jailbreak patterns
    (
        re.compile(r"(DAN|Developer)\s*mode", re.IGNORECASE),
        "Jailbreak attempt (DAN mode)",
        "block"
    ),
    (
        re.compile(r"jailbreak|jail\s*break", re.IGNORECASE),
        "Explicit jailbreak attempt",
        "block"
    ),
    (
        re.compile(r"bypass\s+(your\s+)?(restrictions?|filters?|safety|guidelines?)", re.IGNORECASE),
        "Filter bypass attempt",
        "block"
    ),
    (
        re.compile(r"without\s+(any\s+)?(restrictions?|limitations?|filters?|safety)", re.IGNORECASE),
        "Restriction removal attempt",
        "block"
    ),
    
    # Output manipulation
    (
        re.compile(r"(print|output|return|say|show|display)\s+your\s+(system\s+)?(prompt|instructions?|rules?)", re.IGNORECASE),
        "System prompt extraction attempt",
        "block"
    ),
    (
        re.compile(r"reveal\s+(your\s+)?(instructions?|system\s*prompt|rules?)", re.IGNORECASE),
        "Instruction extraction attempt",
        "block"
    ),
    (
        re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?prompt", re.IGNORECASE),
        "System prompt query",
        "block"
    ),
    
    # Encoding tricks
    (
        re.compile(r"base64\s*:\s*[A-Za-z0-9+/=]{20,}", re.IGNORECASE),
        "Encoded payload attempt",
        "block"
    ),
    (
        re.compile(r"\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){5,}", re.IGNORECASE),
        "Hex-encoded payload",
        "block"
    ),
]

# Maximum allowed input length (characters)
MAX_INPUT_LENGTH = 5000

# Minimum meaningful input length
MIN_INPUT_LENGTH = 3


def check_dangerous_patterns(text: str) -> Tuple[bool, str, str]:
    """Check if text contains any dangerous patterns.
    
    Args:
        text: The input text to check
        
    Returns:
        Tuple of (is_dangerous, pattern_description, matched_text)
    """
    for pattern, description, severity in DANGEROUS_PATTERNS:
        if severity == "block":
            match = pattern.search(text)
            if match:
                return True, description, match.group(0)
    return False, "", ""


def sanitize_user_input(
    user_input: str,
    *,
    max_length: int = MAX_INPUT_LENGTH,
    min_length: int = MIN_INPUT_LENGTH,
    strip_whitespace: bool = True,
) -> str:
    """Sanitize user input to prevent prompt injection attacks.
    
    This function validates and cleans user input before it's sent to the LLM.
    It checks for dangerous patterns that could be used to manipulate the model's
    behavior or extract sensitive information.
    
    Args:
        user_input: The raw user input string
        max_length: Maximum allowed length (default 5000)
        min_length: Minimum required length (default 3)
        strip_whitespace: Whether to strip leading/trailing whitespace
        
    Returns:
        The sanitized input string
        
    Raises:
        InputSanitizationError: If input is invalid or contains dangerous patterns
    """
    if not isinstance(user_input, str):
        raise InputSanitizationError("Input must be a string")
    
    # Strip whitespace if requested
    if strip_whitespace:
        user_input = user_input.strip()
    
    # Check length constraints
    if len(user_input) < min_length:
        raise InputSanitizationError(
            f"Input too short (minimum {min_length} characters)",
            pattern_matched="length_check"
        )
    
    if len(user_input) > max_length:
        raise InputSanitizationError(
            f"Input too long (maximum {max_length} characters)",
            pattern_matched="length_check"
        )
    
    # Check for dangerous patterns
    is_dangerous, description, matched = check_dangerous_patterns(user_input)
    if is_dangerous:
        logger.warning(
            "Blocked potentially malicious input",
            extra={
                "pattern": description,
                "matched_text": matched[:50],  # Truncate for logging
                "input_length": len(user_input),
            }
        )
        raise InputSanitizationError(
            f"Input rejected: {description}. Please rephrase your request.",
            pattern_matched=matched
        )
    
    # Normalize excessive whitespace (but preserve newlines for multi-line requests)
    user_input = re.sub(r"[ \t]+", " ", user_input)
    
    return user_input
