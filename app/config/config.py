"""
Configuration Management System
Handles environment variables, API keys, and application settings
with proper security practices and environment separation
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """AI model configuration settings for text generation and embeddings"""
    embedding_model: str = 'models/text-embedding-004'  # Vector embedding model
    generation_model: str = "gemini-2.0-flash-exp"      # Primary language model
    max_tokens: int = 7000          # Maximum response length
    temperature: float = 0.1        # Response creativity (0=focused, 1=creative)
    top_p: float = 0.9             # Token selection probability threshold
    
@dataclass
class RAGConfig:
    """
    RAG-specific configuration with hybrid search and multi-layer processing
    Balances document retrieval, web search, and confidence thresholds
    """
    # Hybrid Search Settings - Vector similarity thresholds
    embedding_threshold: float = 0.45   # Minimum similarity for document retrieval
    rag_sim_threshold: float = 0.45      # Primary RAG similarity threshold
    bm25_weight: float = 0.4             # BM25 keyword search weight (0=vector only, 1=keyword only)
    top_k_retrieval: int = 8             # Initial document candidates to retrieve
    top_k_rerank: int = 6                # Final documents after reranking
    
    # Self-RAG Settings for iterative improvement
    enable_self_rag: bool = True         # Enable self-correction mechanism
    max_self_rag_iterations: int = 2     # Maximum improvement iterations
    confidence_threshold: float = 0.30   # Minimum confidence for response acceptance
    self_critique_threshold: float = 0.6 # Threshold for self-evaluation
    
    # Web Search Fallback - Triggers when document search insufficient
    enable_web_search: bool = True       # Enable real-time web search
    web_search_threshold: float = 0.30   # Threshold for web search activation
    web_search_max_results: int = 10     # Maximum web results to process
    web_search_similarity: float = 0.55  # Minimum web result relevance
    
    # Mathematical RAG Configuration - Weighted scoring system
    w_doc: float = 1.0          # Document vector similarity weight
    w_bm25: float = 0.5         # BM25 keyword matching weight  
    w_fresh: float = 0.2        # Information freshness weight
    w_lat: float = 0.1          # Latency penalty weight
    tau: float = 3600.0         # Freshness decay constant (1 hour)
    theta: float = 0.55         # Decision threshold
    
    # Context and Response
    max_context_length: int = 8000
    citation_format: str = "〔{doc_id}〕"
    
    # Quality Thresholds
    excellent_threshold: float = 0.8
    good_threshold: float = 0.6
    acceptable_threshold: float = 0.4
    
@dataclass
class SecurityConfig:
    """Security and privacy settings"""
    secret_key: str = "change_this_secret_key_in_production"
    session_timeout: int = 3600  # 1 hour
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    log_level: str = "INFO"
    
@dataclass
class DatabaseConfig:
    """Database and storage configuration"""
    embedding_cache_path: str = "embedding_cache.npy"
    credentials_file: str = "credentials.json"
    sheet_url: str = ""
    backup_interval: int = 86400  # 24 hours

@dataclass
class GoogleSearchConfig:
    """Google Search API configuration"""
    api_key: str = ""
    engine_id: str = ""
    max_results: int = 5
    enabled: bool = True

class ConfigManager:
    """
    Centralized configuration management with environment-based overrides
    """
    
    def __init__(self, env_file: Optional[str] = ".env"):
        self.env_file = env_file
        self._load_environment()
        
        # Initialize configuration objects
        self.model = ModelConfig()
        self.rag = RAGConfig()
        self.security = SecurityConfig()
        self.database = DatabaseConfig()
        self.google_search = GoogleSearchConfig()
        
        # Load from environment variables
        self._load_from_environment()
        
        # Validate critical configurations
        self._validate_config()
        
    def _load_environment(self):
        """Load environment variables from .env file if provided"""
        if self.env_file and Path(self.env_file).exists():
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Error loading .env file: {e}")
    
    def _load_from_environment(self):
        """Override default configs with environment variables"""
        
        # Model configuration
        self.model.embedding_model = os.getenv('EMBEDDING_MODEL', self.model.embedding_model)
        self.model.generation_model = os.getenv('GENERATION_MODEL', self.model.generation_model)
        self.model.max_tokens = int(os.getenv('MAX_TOKENS', self.model.max_tokens))
        self.model.temperature = float(os.getenv('TEMPERATURE', self.model.temperature))
        
        # RAG configuration
        self.rag.embedding_threshold = float(os.getenv('EMBEDDING_THRESHOLD', self.rag.embedding_threshold))
        self.rag.top_k_retrieval = int(os.getenv('TOP_K_RETRIEVAL', self.rag.top_k_retrieval))
        self.rag.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', self.rag.confidence_threshold))
        
        # Security configuration
        self.security.secret_key = os.getenv('SECRET_KEY', self.security.secret_key)
        self.security.log_level = os.getenv('LOG_LEVEL', self.security.log_level)
        
        # Database configuration
        self.database.sheet_url = os.getenv('GOOGLE_SHEET_URL', self.database.sheet_url)
        self.database.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', self.database.credentials_file)
        
        # Google Search configuration
        self.google_search.api_key = os.getenv('GOOGLE_SEARCH_API_KEY', self.google_search.api_key)
        self.google_search.engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID', self.google_search.engine_id)
        self.google_search.enabled = os.getenv('GOOGLE_SEARCH_ENABLED', 'true').lower() == 'true'
        
    def _validate_config(self):
        """Validate critical configuration settings"""
        errors = []
        warnings = []
        
        # Check for required API key (warn but don't fail in development)
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            if self.is_development():
                warnings.append("GOOGLE_API_KEY/GOOGLE_AI_API_KEY environment variable not set (development mode)")
            else:
                errors.append("GOOGLE_API_KEY or GOOGLE_AI_API_KEY environment variable is required")
            
        # Check for credentials file (warn but don't fail if missing)
        if not Path(self.database.credentials_file).exists():
            warnings.append(f"Google credentials file not found: {self.database.credentials_file}")
            
        # Validate ranges
        if not (0 <= self.model.temperature <= 2):
            errors.append("Temperature must be between 0 and 2")
            
        if not (0 <= self.rag.confidence_threshold <= 1):
            errors.append("Confidence threshold must be between 0 and 1")
        
        # Log warnings
        if warnings:
            for warning in warnings:
                logger.warning(warning)
            
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_api_key(self) -> str:
        """Get Google API key with error handling"""
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            raise ValueError("Google API key not found in environment variables")
        return api_key
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return os.getenv('FLASK_ENV', 'development').lower() == 'development'
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary (for debugging)"""
        return {
            'model': {
                'embedding_model': self.model.embedding_model,
                'generation_model': self.model.generation_model,
                'max_tokens': self.model.max_tokens,
                'temperature': self.model.temperature,
            },
            'rag': {
                'embedding_threshold': self.rag.embedding_threshold,
                'top_k_retrieval': self.rag.top_k_retrieval,
                'top_k_rerank': self.rag.top_k_rerank,
                'confidence_threshold': self.rag.confidence_threshold,
            },
            'security': {
                'session_timeout': self.security.session_timeout,
                'rate_limit_requests': self.security.rate_limit_requests,
                'log_level': self.security.log_level,
            },
            'database': {
                'embedding_cache_path': self.database.embedding_cache_path,
                'credentials_file': self.database.credentials_file,
            },
            'environment': {
                'is_development': self.is_development(),
                'is_debug': self.is_debug(),
            }
        }
    
    def save_config_template(self, output_path: str = ".env.example"):
        """Save a configuration template file"""
        template = """# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
GOOGLE_SHEET_URL=your_google_sheet_url_here
GOOGLE_CREDENTIALS_FILE=credentials.json

# Model Configuration
EMBEDDING_MODEL=models/text-embedding-004
GENERATION_MODEL=gemini-2.0-flash
MAX_TOKENS=7000
TEMPERATURE=0.1

# RAG Configuration
EMBEDDING_THRESHOLD=0.75
TOP_K_RETRIEVAL=20
CONFIDENCE_THRESHOLD=0.7

# Security Configuration
SECRET_KEY=your_secret_key_here
LOG_LEVEL=INFO

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
"""
        
        with open(output_path, 'w') as f:
            f.write(template)
        logger.info(f"Configuration template saved to {output_path}")

# Global configuration instance
config = ConfigManager()
