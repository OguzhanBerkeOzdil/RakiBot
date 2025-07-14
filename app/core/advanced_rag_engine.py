"""
Advanced RAG Engine with Ollama/Gemma3 Integration + Web Search + Trakya Dialect
Provides local AI processing with hybrid search capabilities and bilingual support
"""

import logging
import requests
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from functools import lru_cache

# Import Trakya dialect service for authentic Turkish conversation
from app.services.trakya_dialect_service import TrakyaDialectService, trakya_dialect_service

logger = logging.getLogger(__name__)

# Ollama Configuration - Local LLM server settings
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"  # Model for vector embeddings
GENERATION_MODEL = "gemma3:latest"    # Primary text generation model

@dataclass
class RAGResponse:
    """
    Structured response container for RAG system output
    Includes confidence metrics and source attribution
    """
    answer: str
    sources: List[str]
    confidence_score: float
    chunks_used: int
    chunk_quality: str
    response_time: float
    timestamp: str
    mode: str
    web_enhanced: bool = False
    sources_type: str = "general"  # "general", "web", "document"
    web_source_urls: Optional[List[str]] = None  # Actual URLs for web sources

class AdvancedAtlasRAGEngine:
    """
    Advanced RAG Engine with Gemma 3 (Ollama) + Web Search
    Handles document retrieval, query processing, and response generation
    """
    
    def __init__(self):
        """Initialize RAG engine with knowledge base and embeddings"""
        self.knowledge_base = []  # Document store
        self.embeddings = {}      # Vector embeddings cache
        self.ollama_available = False  # Connection status flag
        self.initialize_engine()
    
    def initialize_engine(self):
        """Initialize the RAG engine"""
        try:
            logger.info("🚀 Initializing Advanced RAG Engine with Gemma 3...")
            
            # Check Ollama connection
            self.ollama_available = self._check_ollama_connection()
            
            if self.ollama_available:
                logger.info("✅ Gemma 3 (Ollama) is ready")
            else:
                logger.warning("⚠️ Ollama not available - falling back to basic mode")
            
            # Load local knowledge
            self._load_local_knowledge()
            
            logger.info("✅ Advanced RAG Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ RAG Engine initialization failed: {e}")
    
    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is running and has required models"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if required models are available
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]
            
            has_generation = any(GENERATION_MODEL in name for name in model_names)
            has_embedding = any(EMBEDDING_MODEL in name for name in model_names)
            
            if not has_generation:
                logger.warning(f"⚠️ Generation model {GENERATION_MODEL} not found")
                return False
            
            if not has_embedding:
                logger.warning(f"⚠️ Embedding model {EMBEDDING_MODEL} not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ollama connection check failed: {e}")
            return False
    
    def _load_local_knowledge(self):
        """Load local knowledge base"""
        try:
            knowledge_file = "local_knowledge.json"
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract documents array from the JSON structure
                    if isinstance(data, dict) and 'documents' in data:
                        self.knowledge_base = data['documents']
                    elif isinstance(data, list):
                        self.knowledge_base = data
                    else:
                        self.knowledge_base = []
                logger.info(f"📚 Loaded {len(self.knowledge_base)} knowledge entries")
            else:
                logger.info("📚 No local knowledge file found - creating basic knowledge")
                self.knowledge_base = self._create_basic_knowledge()
                self._save_knowledge()
        except Exception as e:
            logger.error(f"❌ Failed to load knowledge base: {e}")
            self.knowledge_base = []
    
    def _create_basic_knowledge(self) -> List[Dict]:
        """Create basic knowledge entries"""
        return [
            {
                "title": "AI and Machine Learning",
                "content": "Artificial Intelligence (AI) is a branch of computer science that aims to create systems capable of performing tasks that typically require human intelligence.",
                "category": "technology",
                "keywords": ["ai", "artificial intelligence", "machine learning", "technology"]
            },
            {
                "title": "Mathematics",
                "content": "Mathematics is the study of numbers, quantities, shapes, and patterns. It includes arithmetic, algebra, geometry, and calculus.",
                "category": "science",
                "keywords": ["math", "mathematics", "numbers", "calculation", "algebra"]
            },
            {
                "title": "Programming",
                "content": "Programming is the process of creating instructions for computers using programming languages like Python, JavaScript, and Java.",
                "category": "technology",
                "keywords": ["programming", "coding", "software", "development", "python"]
            }
        ]
    
    def _save_knowledge(self):
        """Save knowledge base to file"""
        try:
            with open("local_knowledge.json", 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save knowledge base: {e}")
    
    def _make_ollama_request_with_retry(self, payload: Dict, max_retries: int = 1) -> Any:
        """Make Ollama request with exponential backoff retry"""
        import time
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json=payload,
                    timeout=20  # Reduced from 60 to 20 seconds
                )
                return response
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 0.5  # Reduced wait time: 0.5s, 1s
                    logger.warning(f"⚠️ Ollama request failed (attempt {attempt + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Ollama request failed after {max_retries + 1} attempts: {e}")
                    # Return a mock response for fallback
                    class MockResponse:
                        def __init__(self):
                            self.status_code = 500
                        def json(self): 
                            return {"response": ""}
                    return MockResponse()
    
    @lru_cache(maxsize=128)
    def _generate_embedding_cached(self, text: str) -> Optional[Tuple[float, ...]]:
        """Generate embedding using Ollama with LRU cache"""
        if not self.ollama_available:
            return None
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                # Convert to tuple for caching (lists aren't hashable)
                return tuple(embedding) if embedding else None
            else:
                logger.error(f"❌ Embedding generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Embedding generation error: {e}")
            return None
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using cached function"""
        cached_result = self._generate_embedding_cached(text)
        return list(cached_result) if cached_result else None
    
    def _search_local_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search local knowledge base"""
        if not self.knowledge_base:
            return []
        
        # Simple keyword-based search
        query_words = set(query.lower().split())
        results = []
        
        for entry in self.knowledge_base:
            # Calculate relevance score
            keywords = entry.get("keywords", [])
            content_words = set(entry.get("content", "").lower().split())
            title_words = set(entry.get("title", "").lower().split())
            
            # Score based on keyword matches
            keyword_score = len(query_words.intersection(keywords)) * 2
            content_score = len(query_words.intersection(content_words))
            title_score = len(query_words.intersection(title_words)) * 3
            
            total_score = keyword_score + content_score + title_score
            
            if total_score > 0:
                results.append({
                    "entry": entry,
                    "score": total_score
                })
        
        # Sort by score and return top_k entries (not wrapped)
        results.sort(key=lambda x: x["score"], reverse=True)
        return [r["entry"] for r in results[:top_k]]
    
    def _detect_language(self, text: str) -> str:
        """Detect if the text is Turkish or English - improved version"""
        # Use the enhanced detection from Trakya service
        detected = trakya_dialect_service.detect_language(text)
        
        # Convert to internal format
        if detected == 'en':
            return 'english'
        else:
            return 'turkish'

    def _get_trakya_personality(self) -> Dict[str, Any]:
        """Get Trakya dialect personality traits"""
        base_traits = {
            'humor_style': 'sarcastic_friendly',
            'expressions': [
                'Ya bi dur bakim',  # Hold on a sec
                'Hadi ya!',  # Come on!
                'Ayyyy ne diyosun öyle',  # Oh what are you saying
                'Valla bil bakim',  # I swear, figure it out
                'Hee öyle işte',  # Yeah, that's how it is
                'Yaa naptın yaa',  # Oh what did you do
                'Domuzkuşuuu',  # Porcupine (playful insult)
                'Bi dur hele',  # Wait a minute
                'Gözüm aydın',  # Glad to see you
                'Allah allah',  # Oh my god
            ],
            'speech_patterns': {
                'ending_la': True,  # "güzellaa", "iyilaa"
                'y_insertion': True,  # "koyy", "boyy"
                'vowel_extension': True,  # "çooook", "güzeeeeal"
                'gentle_swearing': True,  # Only for 18+
            },
            'greeting_style': 'warm_sarcastic',
            'advice_style': 'protective_big_sibling'
        }
        
        return base_traits

    def _analyze_query_tone(self, query: str, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze the tone and type of the user's query with user profile context"""
        query_lower = query.lower()
        user_gender = user_profile.get('gender', '') if user_profile else ''
        
        # Detect language first
        language = self._detect_language(query)
        
        # Get Trakya personality traits
        trakya_traits = self._get_trakya_personality()
        
        # Detect casual/friendly indicators (age-appropriate filtering)
        casual_indicators = [
            "bro", "dude", "man", "buddy", "hey", "yo", "sup", "haha", "lol", 
            "cool", "awesome", "chill", "whatever",
            "lol", "haha", "xd", ":)", "😂", "😅", "🤣",
            "chat", "talk", "tell me", "gimme", "wanna", "gonna",
            "whats up", "what's up", "wassup", "whassup", "yooo", "heyy"
        ]
        
        # Turkish casual indicators
        turkish_casual = [
            "ya", "yaa", "lan", "be", "abi", "abla", "moruk", "kanka", "reis",
            "hadi", "haydi", "valla", "vallah", "bil bakim", "naber", "napıyosun",
            "çok iyi", "süper", "harika", "müthiş", "hee", "aynen", "doğru"
        ]
        
        # Adult content indicators (only for 18+)
        adult_casual_indicators = [
            "fuck", "shit", "damn"
        ]
        
        # Turkish adult content 
        turkish_adult_casual = [
            "amk", "lan", "ulan", "vay be", "hay aksi"
        ]
        
        # Add adult indicators (removed age restriction)
        casual_indicators.extend(adult_casual_indicators)
        turkish_casual.extend(turkish_adult_casual)
        
        # Detect strong casual phrases that should override formal detection
        strong_casual_phrases = [
            "whats up", "what's up", "sup", "wassup", "yo", "yooo", "hey man", 
            "whats up man", "what up", "what's good", "how's it going"
        ]
        
        turkish_strong_casual = [
            "naber", "napıyosun", "ne yapıyorsun", "nasılsın", "vay be"
        ]
        
        # Check for strong casual phrases first
        has_strong_casual = any(phrase in query_lower for phrase in strong_casual_phrases)
        has_turkish_strong_casual = any(phrase in query_lower for phrase in turkish_strong_casual)
        
        # Detect formal/serious indicators  
        formal_indicators = [
            "explain", "describe", "information", "research", "learn", "analyze", "evaluate",
            "calculate", "solution", "please kindly", "could you please", "would you please",
            "may i ask", "excuse me", "i would like to know"
        ]
        
        turkish_formal = [
            "açıklayın", "anlatın", "bilgi", "araştırma", "öğrenmek", "analiz", "değerlendirmek",
            "hesaplamak", "çözüm", "lütfen", "acaba", "rica etsem", "özür dilerim"
        ]
        
        # Detect question types
        is_personal = any(word in query_lower for word in [
            "friend", "myself", "girlfriend", "boyfriend", "family", 
            "mother", "father", "brother", "sister", "my", "me", "i am",
            "arkadaş", "kendim", "sevgili", "aile", "anne", "baba", "kardeş", "benim", "ben"
        ])
        
        is_factual = any(word in query_lower for word in [
            "where", "who", "when", "how", "what", "which", 
            "how many", "how much", "define", "meaning",
            "nerede", "kim", "ne zaman", "nasıl", "ne", "hangi", "kaç", "ne kadar", "tanım", "anlam"
        ])
        
        is_technical = any(word in query_lower for word in [
            "code", "program", "software", "technology", "computer", 
            "math", "physics", "algorithm", "database", "api",
            "kod", "program", "yazılım", "teknoloji", "bilgisayar",
            "matematik", "fizik", "algoritma", "veritabanı"
        ])
        
        # Count indicators based on language
        if language == 'turkish':
            casual_score = sum(1 for indicator in turkish_casual if indicator in query_lower)
            formal_score = sum(1 for indicator in turkish_formal if indicator in query_lower)
            has_strong_casual = has_strong_casual or has_turkish_strong_casual
        else:
            casual_score = sum(1 for indicator in casual_indicators if indicator in query_lower)
            formal_score = sum(1 for indicator in formal_indicators if indicator in query_lower)
        
        # Default tone preference (no age restriction)
        tone_preference = "balanced"
        
        # Determine tone - prioritize strong casual phrases
        if has_strong_casual or (casual_score > 0 and casual_score >= formal_score):
            tone = "casual"
        elif is_technical or (formal_score > casual_score and formal_score > 0):
            tone = "formal"
        elif is_personal:
            tone = "friendly"
        else:
            tone = tone_preference
        
        return {
            "tone": tone,
            "language": language,
            "is_personal": is_personal,
            "is_factual": is_factual,
            "is_technical": is_technical,
            "casual_score": casual_score,
            "formal_score": formal_score,
            "user_gender": user_gender,
            "tone_preference": tone_preference,
            "trakya_traits": trakya_traits
        }

    def _generate_direct_answer(self, query: str, user_profile: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """Generate direct answer using Gemma 3 without context - with Trakya dialect support"""
        try:
            # First check for personal responses (Normal mode only) - TEMPORARILY DISABLED FOR DEBUG
            # personal_response = trakya_dialect_service.rakibot_personal_response(query)
            # logger.info(f"🔍 Personal response for '{query[:30]}...': {personal_response is not None}")
            # if personal_response:
            #     logger.info(f"🎯 Using personal response: {personal_response[:50]}...")
            #     return personal_response, 0.95
            
            # Detect language for bilingual support
            detected_language = trakya_dialect_service.detect_language(query)
            
            # Analyze query
            analysis = self._analyze_query_tone(query, user_profile)
            language = analysis["language"]
            tone = analysis["tone"]
            
            # CRITICAL: Always use detected language, not analysis language
            # detected_language is more reliable for input language detection
            if detected_language == 'tr':
                language = 'turkish'
            else:
                language = 'english'
            
            logger.info(f"🌍 Detected language: {detected_language} -> Response language: {language}")
            
            # For other queries, create appropriate response based on DETECTED language
            if detected_language == 'tr':
                # Turkish query processing with Trakya dialect support
                response = self._generate_turkish_response(query, user_profile, tone)
                return response, 0.8
            else:
                # English query processing with Trakya accent
                response = self._generate_english_response(query, user_profile, tone)
                return response, 0.8
                
        except Exception as e:
            logger.error(f"❌ Direct answer generation error: {e}")
            return self._fallback_answer(query), 0.3
    
    def _generate_turkish_response(self, query: str, user_profile: Optional[Dict], tone: str) -> str:
        """Generate Turkish response with Trakya dialect"""
        try:
            # Create appropriate prompt for Turkish with Trakya features
            
            # Determine if Trakya dialect should be used - ONLY when explicitly requested via user_profile
            use_trakya = (user_profile and user_profile.get('tone') == 'trakya') or tone == "trakya"
            
            if use_trakya:
                # Use Trakya dialect with full vocabulary and responses
                style_instruction = """- Samimi ama saygılı bir ton kullanın
- "Canım", "kuzum", "gülüm" gibi sevecen hitaplar kullanın
- Doğru ve işe yarar bilgiler verin
- Anlayışlı ve destekleyici olun
- Tüm kelime hazinesini ve gelişmiş cevapları kullanın
- Kesin ve doğru cevaplar verin, spekülasyon yapmayın"""
                
                # Trakya dialect prompt - improved for accuracy
                prompt = f"""Sen RakıBot'sun, Trakya'dan samimi ama çok akıllı bir AI asistanısın.

ÖNEMLI TALİMATLAR:
{style_instruction}

Sen yardımcı, akıllı ve samimi bir arkadaş gibi davranıyorsun. 
Doğal ve rahat konuşuyorsun ama DOĞRU bilgi vermeye odaklanıyorsun.
Kullanıcının ruh haline uygun karşılık veriyorsun.
Tüm dil becerilerini ve gelişmiş kelime haznesini kullanıyorsun.
YANLIŞ CEVAP VERMEYİN - bilmediğiniz konularda "emin değilim" deyin.

Trakya özellikleri (çok abartmadan, doğal):
- Sadece gerektiğinde "be ya", "canım" kullan
- Bazen "olur->ulur", "olmaz->ulmaz" değişimi
- Samimi ve sıcak yaklaşım
- MUTLAKA akıllı ve DOĞRU cevaplar ver

Soru/Durum: "{query}"

Doğru, kesin ve yardımcı bir cevap ver:"""
            else:
                # Use normal friendly Turkish without any dialect
                style_instruction = """- Doğal, arkadaşça ama saygılı bir ton kullan
- Kısa, net ve işe yarar cevaplar ver
- Fazla formal olma, samimi ol ama saygılı kal
- Gereksiz uzatma, direkt cevabı ver
- Küfür edilirse karşılık ver ama kontrolü kaybetme
- Mental health konularında uzun korumacı konuşma yapma, kısa ve destekleyici ol
- Robot gibi davranma, insan gibi yaklaş"""
                
                # Normal Turkish prompt - less formal, more natural
                prompt = f"""Sen RakıBot'sun, samimi ve yardımcı bir AI asistanısın.

ÖNEMLI TALİMATLAR:
{style_instruction}

Sen arkadaş canlısı, anlayışlı ama robot gibi değil insan gibi konuşan bir yardımcısın.
Kullanıcının ruh haline uygun cevap veriyorsun.
Fazla formal değil, doğal konuşuyorsun.
YANLIŞ bilgi verme - emin değilsen "tam emin değilim" de.

Soru/Durum: "{query}"

Doğal ve yardımcı bir cevap ver:"""
            
            # Adjust generation parameters based on user style and tone
            if tone == "formal":
                temperature = 0.7  # More focused and consistent
                top_p = 0.9
                max_tokens = 250
            elif tone == "casual":
                temperature = 0.85  # Balanced creativity
                top_p = 0.95
                max_tokens = 200
            else:
                temperature = 0.8  # Moderate creativity
                top_p = 0.92
                max_tokens = 200
            
            # Make request to Ollama
            response = self._make_ollama_request_with_retry({
                "model": GENERATION_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens
                }
            }, max_retries=1)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "").strip()
                
                # Apply Trakya dialect post-processing if needed
                if use_trakya and answer:
                    answer = trakya_dialect_service.convert_to_trakya_turkish(
                        answer, 
                        user_profile, 
                        tone,
                        query  # Pass original query for curse detection
                    )
                elif answer:
                    # Apply enhanced Turkish intelligence even without Trakya dialect
                    answer = trakya_dialect_service.enhance_turkish_response(
                        answer,
                        query,
                        user_profile
                    )
                
                return answer if answer else "Üzgünüm, şu anda cevap veremiyorum."
            else:
                return "Üzgünüm, şu anda cevap veremiyorum."
                
        except Exception as e:
            logger.error(f"Turkish response generation error: {e}")
            return "Üzgünüm, bir hata oluştu."
    
    def _generate_english_response(self, query: str, user_profile: Optional[Dict], tone: str) -> str:
        """Generate English response with natural, helpful style"""
        try:
            # Create natural English prompt - more human-like, less robotic
            # Determine if Trakya accent should be used - ONLY when explicitly requested
            use_trakya_accent = (user_profile and user_profile.get('tone') == 'trakya') or tone == "trakya"
            
            if use_trakya_accent:
                # English with Trakya accent/characteristics
                prompt = f"""I'm RakıBot, your friendly AI buddy from Trakya region! I speak with a bit of local flair but I'm smart and helpful.

I keep it real and adapt to how you talk:
- If you're cool with me, I'm cool with you
- If you get salty, I can get a bit salty back while still helping
- If you curse a few times, I might throw some back but keep it helpful
- No fake politeness - I talk like a real person
- I use my full vocabulary and don't hold back

Your question: "{query}"

Let me give you a straight, helpful answer, be ya:"""
            else:
                # Normal English - natural and friendly
                prompt = f"""I'm RakıBot, your friendly AI assistant. I talk like a real person, not a robot.

I match your energy:
- If you're nice, I'm nice
- If you're casual, I'm casual  
- If you get frustrated and curse, I understand and can respond naturally
- If you're having a rough day, I get it and won't lecture you
- No corporate speech - just real, helpful conversation

Your question: "{query}"

Here's my honest, helpful response:"""
            
            # Adjust generation parameters based on user style and tone  
            if tone == "formal":
                temperature = 0.7  # More focused and consistent
                top_p = 0.9
                max_tokens = 250
            elif tone == "casual":
                temperature = 0.85  # Balanced creativity
                top_p = 0.95
                max_tokens = 200
            else:
                temperature = 0.8  # Moderate creativity
                top_p = 0.92
                max_tokens = 200
            
            # Make request to Ollama
            response = self._make_ollama_request_with_retry({
                "model": GENERATION_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens
                }
            }, max_retries=1)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "").strip()
                
                # Apply enhanced English processing
                if answer:
                    # First enhance with advanced English intelligence
                    answer = trakya_dialect_service.enhance_english_response(
                        answer,
                        query,
                        user_profile
                    )
                    
                    # Then apply Trakya accent only if tone is specifically "trakya" or young + casual
                    if tone == "trakya" or tone == "casual":
                        answer = trakya_dialect_service.convert_to_trakya_english(
                            answer, 
                            user_profile,
                            query
                        )
                
                return answer if answer else "Sorry, I cannot answer right now."
            else:
                return "Sorry, I cannot answer right now."
                
        except Exception as e:
            logger.error(f"English response generation error: {e}")
            return "Sorry, an error occurred."

    def _generate_answer_with_gemma(self, query: str, context: str, user_profile: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """Generate answer using Gemma 3 with context - with Trakya dialect support"""
        if not self.ollama_available:
            return self._fallback_answer(query), 0.3
        
        try:
            # Detect language first
            detected_language = trakya_dialect_service.detect_language(query)
            
            # Analyze query tone with user profile
            analysis = self._analyze_query_tone(query, user_profile)
            tone = analysis["tone"]
            # Remove age analysis logic - use full vocabulary and patterns for all users
            # tone is already determined from user profile
            
            # Create appropriate prompt based on detected language
            if detected_language == 'tr':
                # Turkish prompt with context
                prompt = f"""Sen RakıBot'sun, Türkçe konuşan yardımcı bir AI asistanısın.

Sen yardımcı, akıllı ve samimi bir arkadaş gibi davranıyorsun. 
Doğal ve rahat konuşuyorsun ama saygılı kalıyorsun.
Kullanıcının ruh haline uygun karşılık veriyorsun.

Aşağıdaki bilgilere dayanarak soruyu yanıtla:
{context}

Soru: "{query}"

Verilen bilgilere dayanarak doğru ve yararlı bir cevap ver. Yanıtın net, anlaşılır ve verilen bilgilere dayalı olsun:"""
            else:
                # English prompt with context - improved for accuracy
                prompt = f"""I'm RakıBot, your helpful AI assistant. I provide accurate, well-researched answers based on the information provided.

I adapt my communication style to match yours while maintaining accuracy:
- I give clear, factual responses based on the provided information
- I avoid speculation and stick to what's actually stated in the context
- I provide helpful, comprehensive answers that directly address your question
- My responses are professional and informative

Here's the relevant information:
{context}

Your question: "{query}"

Based on the provided information, I'll give you an accurate and helpful answer:"""
            
            # Adjust generation parameters based on detected language and context
            if detected_language == 'tr':
                temperature = 0.8  # Good balance for Turkish responses
                top_p = 0.95
                max_tokens = 300
            else:
                temperature = 0.85  # Slightly higher creativity for English
                top_p = 0.95  
                max_tokens = 300
            
            response = self._make_ollama_request_with_retry({
                "model": GENERATION_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens
                }
            }, max_retries=2)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "").strip()
                
                if answer:
                    # Apply appropriate post-processing based on language and tone
                    if detected_language == 'tr':
                        # Turkish answer - apply Trakya dialect if appropriate
                        # Remove age restrictions - use full vocabulary for all users
                        if tone in ["casual", "friendly", "trakya"]:
                            answer = trakya_dialect_service.convert_to_trakya_turkish(
                                answer, 
                                user_profile, 
                                tone,
                                query  # Pass original query for curse detection
                            )
                    else:
                        # English answer - first enhance with advanced intelligence
                        answer = trakya_dialect_service.enhance_english_response(
                            answer,
                            query,
                            user_profile
                        )
                        
                        # Then apply Trakya accent only if tone is specifically "trakya" or young + casual
                        # Remove age restrictions - use full Trakya dialect for all users  
                        if tone == "trakya" or tone == "casual":
                            answer = trakya_dialect_service.convert_to_trakya_english(
                                answer, 
                                user_profile,
                                query  # Pass original query for curse detection
                            )
                
                # Estimate confidence based on answer quality
                confidence = self._estimate_confidence(query, answer, context)
                
                return answer, confidence
            else:
                logger.error(f"❌ Answer generation failed: {response.status_code}")
                return self._fallback_answer(query, detected_language), 0.3
                
        except Exception as e:
            logger.error(f"❌ Answer generation error: {e}")
            return self._fallback_answer(query), 0.3
    
    def _fallback_answer(self, query: str, language: str = 'english') -> str:
        """Provide fallback answer when Ollama is not available - with Trakya dialect"""
        if language == 'tr' or language == 'turkish':
            base_answer = f"'{query}' akkında soru sorduğunuzu anlıyorum be ya. Şu anda sistem kısıtlamaları nedeniyle detaylı cevap veremiyorum, ama sorunuzu yeniden ifade ederseniz veya web aramasını etkinleştirirseniz daha kapsamlı sonuçlar alabiliriz canım."
            return base_answer
        else:
            return f"I understand you're asking about '{query}', my friend. While I can't provide a detailed answer right now due to system limitations, I'd be happy to help if you could rephrase your question or enable web search for more comprehensive results, be ya!"
    
    def _estimate_confidence(self, query: str, answer: str, context: str) -> float:
        """Estimate confidence score for the answer"""
        if not answer or len(answer.strip()) < 10:
            return 0.1
        
        # Basic heuristics for confidence
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        # Check overlap between query and answer
        query_answer_overlap = len(query_words.intersection(answer_words)) / len(query_words) if query_words else 0
        
        # Check if answer uses context
        answer_context_overlap = len(answer_words.intersection(context_words)) / len(answer_words) if answer_words else 0
        
        # Answer length factor
        length_factor = min(1.0, len(answer.split()) / 50)
        
        # Combine factors
        confidence = (
            0.4 * query_answer_overlap +
            0.3 * answer_context_overlap +
            0.3 * length_factor
        )
        
        return min(0.95, max(0.1, confidence))
    
    def _perform_web_search(self, query: str) -> List[Dict]:
        """Perform web search using enhanced web search service"""
        try:
            logger.info(f"🌐 Web search requested for: {query}")
            
            # Import here to avoid circular imports
            from app.services.enhanced_web_search import EnhancedWebSearchService
            
            web_search_service = EnhancedWebSearchService()
            # Use the secure search method with filtering
            results = web_search_service.search_and_extract(query, max_results=5)
            
            if results:
                logger.info(f"🌐 Found {len(results)} web search results")
                # Process results to ensure they have proper content
                processed_results = []
                for result in results:
                    if result.get('content') or result.get('snippet'):
                        processed_results.append({
                            'title': result.get('title', 'Web Result'),
                            'content': result.get('content', result.get('snippet', '')),
                            'url': result.get('url', ''),
                            'source': 'web_search'
                        })
                return processed_results
            else:
                logger.info("🌐 No web search results found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Web search failed: {e}")
            return []
    
    def _determine_chunk_quality(self, chunks: List[Dict], query: str, confidence_score: float = 0.0) -> str:
        """Determine quality of retrieved chunks based on score"""
        if not chunks:
            return "⚠️ No relevant info"
        
        # Use confidence score if available, otherwise fall back to count
        if confidence_score >= 0.8:
            return "🌟 Excellent"
        elif confidence_score >= 0.6:
            return "✨ Very Good"  
        elif confidence_score >= 0.4:
            return "👍 Good"
        elif confidence_score >= 0.3:
            return "⚠️ Limited"
        else:
            # Fall back to chunk count for backward compatibility
            if len(chunks) >= 3:
                return "🌟 Excellent"
            elif len(chunks) >= 2:
                return "✨ Very Good"
            elif len(chunks) >= 1:
                return "👍 Good"
            else:
                return "📝 Basic"
    
    def process_question(self, user_question: str, enable_web_search: bool = False, chat_mode: str = "normal", user_profile: Optional[Dict[str, Any]] = None) -> RAGResponse:
        """
        Main entry point for processing questions
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Processing question: {user_question[:100]}...")
            logger.info(f"📊 Mode: {chat_mode}, Web Search: {enable_web_search}")
            
            context = ""
            web_enhanced = False
            local_results = []
            sources = []
            web_source_urls = []
            sources_type = "general"
            
            # If web search is enabled, search web first
            if enable_web_search:
                logger.info("🌐 Performing web search...")
                web_results = self._perform_web_search(user_question)
                if web_results:
                    logger.info(f"🌐 Found {len(web_results)} web results")
                    context_parts = []
                    for result in web_results:
                        context_parts.append(result.get("content", ""))
                        # Store actual URLs
                        if result.get("url"):
                            web_source_urls.append(result.get("url"))
                    context = "\n\n".join(context_parts)
                    web_enhanced = True
                    sources_type = "web"
                    # Use web results as "local_results" for chunk counting
                    local_results = web_results
                    # Create sources with actual web source info
                    sources = [f"🌐 {result.get('title', 'Web Result')}" for result in web_results]
            
            # Generate answer
            if context.strip():
                answer, confidence = self._generate_answer_with_gemma(user_question, context, user_profile)
                
                # Add web search footer if using web results
                if web_enhanced and web_source_urls:
                    answer += f"\n\n🌐 *This answer is based on web search results.*"
            else:
                # No context available - use Ollama directly for general questions
                if self.ollama_available:
                    answer, confidence = self._generate_direct_answer(user_question, user_profile)
                else:
                    answer = self._fallback_answer(user_question)
                    confidence = 0.3
            
            # Determine chunk quality
            chunk_quality = self._determine_chunk_quality(local_results, user_question, confidence)
            
            response_time = time.time() - start_time
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=confidence,
                chunks_used=len(local_results),
                chunk_quality=chunk_quality,
                response_time=response_time,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                mode="GEMMA3_WEB" if web_enhanced else "GEMMA3_DIRECT",
                web_enhanced=web_enhanced,
                sources_type=sources_type,
                web_source_urls=web_source_urls if web_source_urls else None
            )
            
        except Exception as e:
            logger.error(f"❌ Question processing failed: {e}")
            return RAGResponse(
                answer="Sorry, there was an error processing your question.",
                sources=[],
                confidence_score=0.1,
                chunks_used=0,
                chunk_quality="❌ Hata",
                response_time=0.0,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                mode="ERROR",
                web_enhanced=False,
                sources_type="general",
                web_source_urls=None
            )
