"""
Enhanced Embedding Service
Advanced document processing, embedding generation, and retrieval
with performance optimizations and robust error handling
"""

import os
import re
import json
import time
import hashlib
import pickle
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False

try:
    import gspread  # type: ignore
    from google.oauth2.service_account import Credentials  # type: ignore
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

try:
    import google.generativeai as genai  # type: ignore
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from nltk.corpus import stopwords
    import nltk
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

from app.config.config import config

# Download required NLTK data
if HAS_NLTK:
    try:
        nltk.download("stopwords", quiet=True)
        nltk.download("punkt", quiet=True)
    except:
        pass

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """Advanced caching system for embeddings with TTL and invalidation"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.ttl_hours = 24 * 7  # 1 week
        
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model"""
        combined = f"{text}:{model}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[np.ndarray]:
        """Retrieve embedding from cache if valid"""
        try:
            cache_key = self._get_cache_key(text, model)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            if not cache_file.exists():
                return None
                
            # Check if cache is still valid
            metadata = self._load_metadata()
            if cache_key not in metadata:
                return None
                
            cache_time = datetime.fromisoformat(metadata[cache_key]["timestamp"])
            if datetime.now() - cache_time > timedelta(hours=self.ttl_hours):
                self._invalidate_entry(cache_key)
                return None
                
            # Load embedding
            with open(cache_file, 'rb') as f:
                embedding = pickle.load(f)
                
            return embedding
            
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None
    
    def set(self, text: str, model: str, embedding: np.ndarray):
        """Store embedding in cache"""
        try:
            cache_key = self._get_cache_key(text, model)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            # Save embedding
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
                
            # Update metadata
            metadata = self._load_metadata()
            metadata[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "text_length": len(text)
            }
            self._save_metadata(metadata)
            
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def _load_metadata(self) -> Dict:
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_metadata(self, metadata: Dict):
        """Save cache metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _invalidate_entry(self, cache_key: str):
        """Remove cache entry"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            cache_file.unlink()
            
        metadata = self._load_metadata()
        if cache_key in metadata:
            del metadata[cache_key]
            self._save_metadata(metadata)
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        metadata = self._load_metadata()
        now = datetime.now()
        expired_keys = []
        
        for key, data in metadata.items():
            cache_time = datetime.fromisoformat(data["timestamp"])
            if now - cache_time > timedelta(hours=self.ttl_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._invalidate_entry(key)
            
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

class AdvancedEmbeddingService:
    """
    Enhanced embedding service with performance optimizations,
    better error handling, and advanced document processing
    """
    
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        self.credentials_file = config.database.credentials_file
        self.embedding_model = config.model.embedding_model
        self.generation_model = config.model.generation_model
        
        # Initialize API
        if HAS_GENAI:
            try:
                import google.generativeai as genai_config  # type: ignore
                genai_config.configure(api_key=config.get_api_key())  # type: ignore
            except Exception as e:
                logger.warning(f"Could not configure Google AI: {e}")
        
        # Initialize cache
        self.cache = EmbeddingCache()
        
        # Initialize stopwords
        if HAS_NLTK:
            try:
                self.stop_words = set(stopwords.words("english"))
            except:
                self.stop_words = set()
        else:
            self.stop_words = set()
            
        # Performance metrics
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'total_processing_time': 0.0
        }
        
        # Document storage
        self.df: Any = None
        self.embeddings_loaded = False
        
    def load_data(self, sheet_url: Optional[str] = None) -> pd.DataFrame:
        """
        Load data from Google Sheets with fallback to local JSON
        """
        start_time = time.time()
        
        try:
            sheet_url = sheet_url or config.database.sheet_url
            if not sheet_url:
                # Fallback to local knowledge
                logger.info("No Google Sheet URL provided, using local knowledge...")
                return self._load_local_knowledge()
                
            logger.info("Loading data from Google Sheets...")
            
            # Setup credentials
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=self.scopes
            )
            gc = gspread.authorize(creds)
            
            # Open spreadsheet
            sheet = gc.open_by_url(sheet_url)
            worksheet = sheet.sheet1
            
            # Get all values
            rows = worksheet.get_all_values()
            if not rows:
                raise ValueError("No data found in spreadsheet")
                
            header, *data = rows
            df = pd.DataFrame(data, columns=header)
            
            # Data validation
            required_columns = ['Title', 'Content']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
                
            # Clean data
            df = df.dropna(subset=required_columns)
            df = df[df['Content'].str.strip() != ''].copy()
            
            logger.info(f"Loaded {len(df)} documents in {time.time() - start_time:.2f}s")
            
            # Ensure it's a proper DataFrame
            self.df = df.reset_index(drop=True)
            return self.df
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def embed_document(self, title: str, content: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a document with caching
        """
        if not HAS_ML_LIBS:
            raise ImportError("NumPy required for embeddings")
            
        if not HAS_GENAI:
            raise ImportError("Google Generative AI required for embeddings")
            
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cached_embedding = self.cache.get(content, self.embedding_model)
                if cached_embedding is not None:
                    self.metrics['cache_hits'] += 1
                    return cached_embedding
                self.metrics['cache_misses'] += 1
            
            # Generate embedding via API
            if not HAS_GENAI:
                raise Exception("Google AI not available")
            
            self.metrics['api_calls'] += 1
            response = genai.embed_content(  # type: ignore
                model=self.embedding_model,
                content=content,
                task_type="retrieval_document",
                title=title
            )
            
            embedding = np.array(response['embedding'])
            
            # Cache the result
            if use_cache:
                self.cache.set(content, self.embedding_model, embedding)
            
            processing_time = time.time() - start_time
            self.metrics['total_processing_time'] += processing_time
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding for '{title}': {e}")
            raise
    
    def prepare_embeddings(self, df: Optional[pd.DataFrame] = None, 
                         force_refresh: bool = False) -> pd.DataFrame:
        """
        Prepare embeddings for all documents with batch processing
        """
        if df is None:
            if self.df is not None:
                df = self.df
            else:
                raise ValueError("No dataframe provided and none loaded")
                
        # Ensure df is not None for type checking
        assert df is not None
            
        cache_path = config.database.embedding_cache_path
        
        # Load from numpy cache if available and not forcing refresh
        if not force_refresh and os.path.exists(cache_path):
            try:
                logger.info("Loading embeddings from cache...")
                embeddings = np.load(cache_path, allow_pickle=True)
                if len(embeddings) == len(df):
                    df = df.copy()  # Make a copy to avoid modifying original
                    df['Embedding'] = embeddings
                    self.embeddings_loaded = True
                    logger.info(f"Loaded {len(embeddings)} cached embeddings")
                    return df
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(df)} documents...")
        embeddings = []
        
        for i, row in enumerate(df.itertuples(index=False)):
            try:
                # Convert to string to ensure proper types
                title = str(row.Title)
                content = str(row.Content)
                embedding = self.embed_document(title, content)
                embeddings.append(embedding)
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Generated {i + 1}/{len(df)} embeddings")
                    
            except Exception as e:
                logger.error(f"Failed to generate embedding for row {i}: {e}")
                # Use zero vector as fallback
                embeddings.append(np.zeros(768))  # Default embedding size
        
        df = df.copy()  # Make a copy before modifying
        df['Embedding'] = embeddings
        
        # Save to cache
        try:
            np.save(cache_path, df['Embedding'].to_numpy())
            logger.info(f"Saved embeddings to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
        
        self.embeddings_loaded = True
        return df
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text (alias for embed_question)"""
        return self.embed_question(text)
    
    def find_similar_chunks(self, query: str, df: pd.DataFrame, top_k: int = 5) -> List[int]:
        """Find similar chunks for additional retrieval (alias for retrieve_relevant_chunks)"""
        question_embedding = self.generate_embedding(query)
        return self.retrieve_relevant_chunks(df, question_embedding, top_k=top_k)
    
    def embed_question(self, question: str) -> Optional[np.ndarray]:
        """Generate embedding for a question"""
        if not HAS_ML_LIBS:
            logger.error("NumPy required for embeddings")
            return None
            
        if not HAS_GENAI:
            logger.error("Google Generative AI required for embeddings")
            return None
            
        try:
            logger.info(f"Generating embedding for question: {question[:50]}...")
            response = genai.embed_content(  # type: ignore
                model=self.embedding_model,
                content=question,
                task_type="retrieval_query"
            )
            embedding = np.array(response["embedding"])
            logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Error generating question embedding: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"API Key available: {'GOOGLE_API_KEY' in os.environ}")
            logger.error(f"Model: {self.embedding_model}")
            return None
    
    def retrieve_relevant_chunks(self, df: pd.DataFrame, question_embedding: Optional[np.ndarray],
                               threshold: Optional[float] = None, top_k: Optional[int] = None) -> List[int]:
        """
        Enhanced document retrieval with configurable parameters
        """
        if not HAS_ML_LIBS:
            logger.warning("ML libraries not available, returning empty results")
            return []
            
        if question_embedding is None:
            logger.error("Question embedding is None, cannot retrieve documents")
            return []
            
        threshold = threshold or config.rag.embedding_threshold
        top_k = top_k or config.rag.top_k_retrieval
        
        try:
            logger.info(f"DataFrame shape: {df.shape}")
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
            logger.info(f"Has Embedding column: {'Embedding' in df.columns}")
            
            if 'Embedding' not in df.columns:
                logger.error("No Embedding column in DataFrame")
                return []
                
            if df.empty:
                logger.error("DataFrame is empty")
                return []
            
            # Stack all embeddings - convert Series to list first
            embedding_list = df['Embedding'].tolist()
            logger.info(f"Number of embeddings: {len(embedding_list)}")
            
            if not embedding_list:
                logger.error("No embeddings found in DataFrame")
                return []
                
            # Check if embeddings are valid
            valid_embeddings = [emb for emb in embedding_list if emb is not None and len(emb) > 0]
            if not valid_embeddings:
                logger.error("No valid embeddings found")
                return []
                
            all_embeddings = np.stack(valid_embeddings)
            logger.info(f"Stacked embeddings shape: {all_embeddings.shape}")
            
            # Calculate similarities
            similarities = cosine_similarity(
                np.array([question_embedding]), 
                all_embeddings
            )[0]
            
            # Apply threshold filter
            above_threshold = np.where(similarities > threshold)[0]
            
            if len(above_threshold) == 0:
                # Fall back to top-k if no documents meet threshold
                indices = np.argsort(similarities)[-top_k:]
                logger.warning(f"No documents above threshold {threshold}, using top {top_k}")
            else:
                # Get top-k from above threshold
                threshold_similarities = similarities[above_threshold]
                sorted_indices = np.argsort(threshold_similarities)[-top_k:]
                indices = above_threshold[sorted_indices]
            
            # Sort by similarity (descending)
            indices = indices[np.argsort(similarities[indices])[::-1]]
            
            return indices.tolist()
            
        except Exception as e:
            logger.error(f"Error in document retrieval: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            return []
    
    def embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not HAS_ML_LIBS or not HAS_GENAI:
            logger.warning("Required libraries not available for similarity calculation")
            return 0.0
            
        try:
            emb1 = self.embed_question(text1)
            emb2 = self.embed_question(text2)
            
            # Convert to 2D arrays for cosine_similarity
            emb1_2d = np.array([emb1])
            emb2_2d = np.array([emb2])
            
            return float(cosine_similarity(emb1_2d, emb2_2d)[0][0])
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def extract_section_number(self, title: str) -> Optional[str]:
        """Extract section number from document title"""
        match = re.search(r'§\s*(\d+(?:\.\d+)?)', title)
        return match.group(1) if match else None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance and usage metrics"""
        total_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = self.metrics['cache_hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'cache_hit_rate': round(cache_hit_rate, 3),
            'total_api_calls': self.metrics['api_calls'],
            'average_processing_time': round(
                self.metrics['total_processing_time'] / max(1, self.metrics['api_calls']), 3
            ),
            'embeddings_loaded': self.embeddings_loaded,
            'documents_count': len(self.df) if self.df is not None else 0
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service"""
        health = {
            'status': 'healthy',
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check API connectivity
        try:
            test_embedding = self.embed_question("test")
            if test_embedding is None or len(test_embedding) == 0:
                health['issues'].append("API returned empty or None embedding")
        except Exception as e:
            health['issues'].append(f"API connectivity issue: {e}")
        
        # Check data availability
        if self.df is None or len(self.df) == 0:
            health['issues'].append("No documents loaded")
        
        # Check embeddings
        if not self.embeddings_loaded:
            health['issues'].append("Embeddings not prepared")
        
        # Overall status
        if health['issues']:
            health['status'] = 'degraded' if len(health['issues']) < 3 else 'unhealthy'
        
        return health
    
    def _load_local_knowledge(self) -> pd.DataFrame:
        """
        Load data from local JSON file as fallback
        """
        try:
            local_file = 'local_knowledge.json'
            if not os.path.exists(local_file):
                logger.warning("No local knowledge file found, creating empty dataset")
                return pd.DataFrame(columns=['Title', 'Content', 'Source'])
            
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            if 'documents' in data:
                documents = data['documents']
            else:
                documents = data
            
            df = pd.DataFrame(documents)
            
            # Ensure required columns exist
            if 'Title' not in df.columns and 'title' in df.columns:
                df = df.rename(columns={'title': 'Title'})
            if 'Content' not in df.columns and 'content' in df.columns:
                df = df.rename(columns={'content': 'Content'})
            if 'Source' not in df.columns:
                df['Source'] = 'Local Knowledge'
            
            logger.info(f"Loaded {len(df)} documents from local knowledge")
            return df
            
        except Exception as e:
            logger.error(f"Error loading local knowledge: {e}")
            return pd.DataFrame(columns=['Title', 'Content', 'Source'])
