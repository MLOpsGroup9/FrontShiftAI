"""
LLM Configuration for Agents
Simple code-based switching between providers
"""

# ============================================
# AGENT LLM CONFIGURATION
# Change this to switch providers instantly
# ============================================

USE_LLM = "groq"  # Options: "groq", "local", "mercury", "openai"

# Fallback enabled?
ENABLE_FALLBACK = True  # Set False to disable fallback

# If fallback enabled, try in this order
FALLBACK_CHAIN = ["groq", "mercury", "openai", "local"]

# ============================================
# PROVIDER CONFIGURATIONS
# ============================================

GROQ_CONFIG = {
    "api_key": None,  # Will be loaded from .env
    "model": "llama-3.1-8b-instant",  # Updated model
    "temperature": 0.7,
    "max_tokens": 2000,
}

LOCAL_CONFIG = {
    "url": "http://localhost:11434",  # Ollama default
    "model": "llama3:3b",
    "temperature": 0.7,
    "max_tokens": 2000,
}

MERCURY_CONFIG = {
    "api_url": None,  # Will be loaded from .env
    "api_key": None,  # Will be loaded from .env
    "model": "mercury-model",
    "temperature": 0.7,
    "max_tokens": 2000,
}

OPENAI_CONFIG = {
    "api_key": None,  # Will be loaded from .env
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2000,
}