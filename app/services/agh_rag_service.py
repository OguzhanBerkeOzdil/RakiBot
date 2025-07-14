"""
AGH RAG Service - Advanced document retrieval for AGH regulations
Based on the successful Example_rag_agh implementation - Now with Gemma 3 (Ollama)
"""

import os
import re
import time as time_module  # Import with alias to avoid conflicts
import numpy as np
import pandas as pd
import logging
import requests
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import gspread
from google.oauth2.service_account import Credentials
from nltk.corpus import stopwords
import nltk

# Download stopwords if not already downloaded
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download("stopwords")

logger = logging.getLogger(__name__)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Ollama Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"  # For embeddings
GENERATION_MODEL = "gemma3:latest"  # For text generation

@dataclass
class AGHResponse:
    """Response from AGH RAG system"""
    answer: str
    sources: str
    trust_score: float
    warning: Optional[str]
    section_refs: List[str]
    language: str
    tokens: int
    processing_time: float
    sources_type: str = "document"  # "document" or "web"

class AGHRAGService:
    """
    Advanced AGH RAG Service with Gemma 3 (Ollama) integration
    Document retrieval, section citation, and trust scoring
    """
    
    def __init__(self):
        self.df = None
        self.embedding_cache_path = "agh_embedding_cache.npy"
        self.sheet_url = "https://docs.google.com/spreadsheets/d/15IrW43TtKJExLW2FRSFabwWKex_SCVWjE3ii34iH67g/edit?gid=0"
        self.initialize_service()
    
    def initialize_service(self):
        """Initialize the AGH RAG service"""
        try:
            logger.info("🔧 Initializing AGH RAG Service with Gemma 3...")
            
            # Check Ollama connection
            if not self._check_ollama_connection():
                logger.error("❌ Ollama connection failed")
                return False
            
            # Load data and prepare embeddings
            self.df = self._load_data_from_sheets()
            if self.df is not None:
                self.df = self._prepare_embeddings(self.df)
                logger.info(f"✅ AGH RAG Service initialized with {len(self.df)} documents")
                return True
            else:
                logger.error("❌ Failed to load AGH data")
                return False
                
        except Exception as e:
            logger.error(f"❌ AGH RAG Service initialization failed: {e}")
            return False
    
    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama connection established")
                return True
            else:
                logger.error(f"❌ Ollama responded with status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Ollama connection failed: {e}")
            return False
    
    def _load_data_from_sheets(self) -> Optional[pd.DataFrame]:
        """Load data from Google Sheets"""
        try:
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                logger.error(f"❌ Service account file not found: {SERVICE_ACCOUNT_FILE}")
                return None
            
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            gc = gspread.authorize(creds)
            sheet = gc.open_by_url(self.sheet_url)
            worksheet = sheet.sheet1
            rows = worksheet.get_all_values()
            
            if not rows:
                logger.error("❌ No data found in Google Sheets")
                return None
            
            header, *data = rows
            df = pd.DataFrame(data, columns=header)
            logger.info(f"✅ Loaded {len(df)} rows from Google Sheets")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load data from Google Sheets: {e}")
            return None
    
    def _generate_embedding(self, text: str, title: str = "") -> Optional[List[float]]:
        """Generate embedding using Ollama"""
        try:
            # Combine title and content for better embeddings
            content = f"{title}\n{text}" if title else text
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": content
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"❌ Embedding generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Embedding generation error: {e}")
            return None
    
    def _prepare_embeddings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare embeddings for all documents"""
        try:
            # Check cache first
            if os.path.exists(self.embedding_cache_path):
                logger.info("📂 Loading cached embeddings...")
                cached_embeddings = np.load(self.embedding_cache_path, allow_pickle=True)
                if len(cached_embeddings) == len(df):
                    df['Embedding'] = cached_embeddings
                    logger.info("✅ Cached embeddings loaded")
                    return df
            
            logger.info("🔄 Generating embeddings with Ollama...")
            embeddings = []
            
            for i, (idx, row) in enumerate(df.iterrows()):
                title = row.get('Title', '')
                content = row.get('Content', '')
                
                embedding = self._generate_embedding(content, title)
                if embedding:
                    embeddings.append(embedding)
                else:
                    # Fallback: create zero embedding
                    embeddings.append([0.0] * 768)  # Default embedding size
                
                if (i + 1) % 5 == 0:
                    logger.info(f"📊 Generated {i + 1}/{len(df)} embeddings")
            
            df['Embedding'] = embeddings
            
            # Save to cache
            np.save(self.embedding_cache_path, df['Embedding'].to_numpy())
            logger.info("💾 Embeddings cached successfully")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Embedding preparation failed: {e}")
            return df
    
    def _embed_question(self, question: str) -> Optional[List[float]]:
        """Generate embedding for a question"""
        return self._generate_embedding(question)
    
    def _retrieve_relevant_chunks(self, question_embedding: List[float], threshold: float = 0.75, top_k: int = 3) -> List[int]:
        """Retrieve relevant document chunks"""
        try:
            if self.df is None or question_embedding is None:
                return []
            
            # Convert embeddings to numpy array properly
            embeddings_list = [emb for emb in self.df['Embedding'].values if emb is not None]
            if not embeddings_list:
                return []
                
            all_embeddings = np.array(embeddings_list)
            question_vec = np.array(question_embedding)
            
            # Calculate cosine similarity
            dot_products = np.dot(all_embeddings, question_vec)
            norms = np.linalg.norm(all_embeddings, axis=1) * np.linalg.norm(question_vec)
            similarities = dot_products / (norms + 1e-8)
            
            # Filter by threshold
            indices = np.where(similarities > threshold)[0]
            
            if len(indices) == 0:
                # If no documents meet threshold, take top_k
                indices = np.argsort(similarities)[-top_k:]
            
            # Sort by similarity (highest first)
            sorted_indices = indices[np.argsort(similarities[indices])[::-1]]
            
            return sorted_indices.tolist()
            
        except Exception as e:
            logger.error(f"❌ Chunk retrieval failed: {e}")
            return []
    
    def _build_prompt(self, chunks: List[str], metadata: List[Dict], question: str, user_profile: Optional[Dict] = None, max_tokens: int = 7000) -> Tuple[str, List[str], List[Dict]]:
        """Build prompt from relevant chunks"""
        def estimate_tokens(text: str) -> int:
            return int(len(text.split()) * 1.3)
        
        # Build user context for adaptive responses (internal instructions only)
        user_context = ""
        if user_profile and (user_profile.get('age') or user_profile.get('gender')):
            context_parts = []
            if user_profile.get('age'):
                context_parts.append(f"age group: {user_profile['age']}")
            if user_profile.get('gender'):
                context_parts.append(f"gender: {user_profile['gender']}")
            
            if context_parts:
                # Internal instruction - don't mention this adaptation in the response
                user_context = f"\nINTERNAL INSTRUCTION: Adapt your answer tone and language complexity for someone with {', '.join(context_parts)}. Use appropriate language level but DO NOT mention this adaptation in your response.\n"
        
        prompt = f"""QUESTION: {question}{user_context}

Please answer based on the following AGH University regulations. Follow these guidelines:

📋 RESPONSE FORMAT:
- Keep your answer CONCISE and FOCUSED (2-3 paragraphs maximum)
- Extract only the ESSENTIAL information that directly answers the question
- Include section references (e.g., §19) when citing specific rules
- Use bullet points for lists to improve readability
- Avoid lengthy explanations unless specifically requested

🎯 ANSWER STYLE:
- Be direct and to-the-point
- Prioritize the most important information first
- If there's a lot of detail, summarize the key points
- Use clear, simple language
- CRITICAL: Distinguish between different concepts:
  * "Passing grade" = minimum score to pass an exam (typically 60/100)
  * "ECTS credits" = credit accumulation for graduation
  * "Graduation requirements" = total credits needed to graduate
  * "Thesis requirements" = specific requirements for thesis/dissertation
- Match your answer EXACTLY to what was asked - don't mix up grades with credits!

REGULATIONS:
"""
        
        final_chunks = []
        final_metadata = []
        
        for chunk, meta in zip(chunks, metadata):
            test_prompt = prompt + chunk + "\n\n"
            if estimate_tokens(test_prompt) > max_tokens:
                break
            
            prompt = test_prompt
            final_chunks.append(chunk)
            final_metadata.append(meta)
        
        return prompt, final_chunks, final_metadata
    
    def _generate_answer(self, prompt: str) -> Tuple[str, int]:
        """Generate answer using Gemma 3"""
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": GENERATION_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "").strip()
                # Estimate tokens (Ollama doesn't provide exact count)
                tokens = len(prompt.split()) + len(answer.split())
                return answer, tokens
            else:
                logger.error(f"❌ Answer generation failed: {response.status_code}")
                return "Sorry, I couldn't generate an answer.", 0
                
        except Exception as e:
            logger.error(f"❌ Answer generation error: {e}")
            return "Sorry, there was an error generating the answer.", 0
    
    def _extract_section_number(self, title: str) -> str:
        """Extract section number from title"""
        match = re.search(r'§\s*(\d+(?:\.\d+)?)', title)
        return match.group(1) if match else "N/A"
    
    def _calculate_trust_score(self, question: str, answer: str, chunks: List[str]) -> float:
        """Calculate trust score based on multiple factors"""
        try:
            # 1. Keyword overlap
            stop_words = set(stopwords.words("english"))
            q_words = set(re.findall(r'\b\w+\b', question.lower())) - stop_words
            a_words = set(re.findall(r'\b\w+\b', answer.lower()))
            keyword_overlap = len(q_words & a_words) / len(q_words) if q_words else 0
            
            # 2. Important terms presence
            important_terms = {"examination", "semester", "faculty", "student", "regulation", "grade", "credit"}
            q_important = set(re.findall(r'\b\w+\b', question.lower())) & important_terms
            a_important = set(re.findall(r'\b\w+\b', answer.lower())) & important_terms
            term_score = len(q_important & a_important) / len(q_important) if q_important else 0.5
            
            # 3. Content overlap with source chunks
            chunk_text = " ".join(chunks)
            chunk_words = set(re.findall(r'\b\w+\b', chunk_text.lower()))
            content_overlap = len(a_words & chunk_words) / len(a_words) if a_words else 0
            
            # 4. Answer quality (length and structure)
            quality_score = min(1.0, len(answer.split()) / 50)  # Normalize by 50 words
            
            # Combine scores
            trust_score = (
                0.3 * keyword_overlap +
                0.2 * term_score +
                0.3 * content_overlap +
                0.2 * quality_score
            )
            
            return round(trust_score, 3)
            
        except Exception as e:
            logger.error(f"❌ Trust score calculation failed: {e}")
            return 0.5
    
    def _is_low_quality_answer(self, question: str, answer: str) -> bool:
        """Check if answer is low quality"""
        if not answer or len(answer.split()) <= 2:
            return True
        
        if question.lower() in answer.lower():
            return True
        
        # Check for generic responses
        generic_phrases = ["i don't know", "unclear", "cannot determine", "not specified"]
        if any(phrase in answer.lower() for phrase in generic_phrases):
            return True
        
        return False
    
    def _fix_known_errors(self, answer: str) -> str:
        """Fix known incorrect information from Google Sheets data"""
        try:
            # Fix passing grade - Google Sheets incorrectly shows 60/100, should be 50/100
            answer = re.sub(r'\b60/100\b', '50/100', answer)
            answer = re.sub(r'\b60 out of 100\b', '50 out of 100', answer)
            answer = re.sub(r'typically 60/100', 'typically 50/100', answer)
            answer = re.sub(r'generally 60/100', 'generally 50/100', answer)
            answer = re.sub(r'passing.*?60', 'passing grade is 50', answer, flags=re.IGNORECASE)
            
            # Log when corrections are made
            if '50/100' in answer or '50 out of 100' in answer:
                logger.info("🔧 Corrected passing grade from 60 to 50 (Google Sheets data fix)")
            
            return answer
        except Exception as e:
            logger.error(f"Error fixing known errors: {e}")
            return answer
    
    def answer_question(self, question: str, enable_web_search: bool = False, user_profile: Optional[Dict] = None) -> AGHResponse:
        """
        Answer a question using AGH regulations
        Main entry point for the AGH RAG system
        """
        start_time = time_module.time()
        
        # Count input tokens for AGH mode only (like original AGH expert)
        input_tokens = len(question.split())
        logger.info(f"📊 Input Token Count: {input_tokens}")
        
        # Check if user explicitly requests web search with keywords
        question_lower = question.lower().strip()
        web_search_keywords = ["search", "google", "web search", "search on google", "search web"]
        has_search_keyword = any(keyword in question_lower for keyword in web_search_keywords)
        
        # If user includes search keywords OR web search is enabled, enable web search
        if has_search_keyword:
            enable_web_search = True
            # Clean up the question by removing search keywords
            for keyword in web_search_keywords:
                question = question.replace(keyword, "").strip()
            logger.info("🔍 User requested web search in AGH mode")
        elif enable_web_search:
            logger.info("🌐 Web search enabled for AGH mode")
        
        try:
            if self.df is None:
                return AGHResponse(
                    answer="AGH RAG service is not properly initialized.",
                    sources="N/A",
                    trust_score=0.0,
                    warning="Service initialization error",
                    section_refs=[],
                    language="en",
                    tokens=input_tokens,
                    processing_time=0.0,
                    sources_type="document"
                )
            
            # Generate question embedding
            question_embedding = self._embed_question(question)
            if not question_embedding:
                return AGHResponse(
                    answer="Sorry, I couldn't process your question.",
                    sources="N/A",
                    trust_score=0.0,
                    warning="Embedding generation failed",
                    section_refs=[],
                    language="en",
                    tokens=input_tokens,
                    processing_time=time_module.time() - start_time,
                    sources_type="document"
                )
            
            # Retrieve relevant chunks
            indices = self._retrieve_relevant_chunks(question_embedding)
            
            # If web search is explicitly enabled, prioritize web search for better real-time information
            if enable_web_search:
                logger.info("🌐 Performing web search for AGH regulations (web search explicitly enabled)...")
                try:
                    from app.services.enhanced_web_search import EnhancedWebSearchService
                    web_search = EnhancedWebSearchService()
                    
                    # Focus search specifically on AGH University of Krakow
                    agh_search_query = f"AGH University of Science and Technology Krakow regulations {question}"
                    search_results = web_search.search_and_extract(agh_search_query, max_results=5)
                    
                    if search_results:
                        # Build web search answer focused on AGH
                        web_content = []
                        sources = []
                        for result in search_results[:5]:
                            if result.get('snippet'):
                                web_content.append(f"• {result['snippet']}")
                            if result.get('url'):
                                sources.append(result['url'])
                        
                        # Create AGH-focused web search answer
                        web_prompt = f"""Question about AGH University of Science and Technology Krakow: {question}

📋 RESPONSE FORMAT:
- Keep your answer CONCISE and FOCUSED (2-3 paragraphs maximum)
- Extract only the ESSENTIAL information that directly answers the question
- Use bullet points for lists to improve readability
- Be direct and to-the-point

Based on web search results about AGH regulations:

{chr(10).join(web_content)}

Please provide a concise, helpful answer specifically about AGH University regulations based on these web search results. If the results don't contain AGH-specific information, clearly state that."""
                        
                        answer, tokens_generated = self._generate_answer(web_prompt)
                        total_tokens = input_tokens + tokens_generated
                        sources_text = ", ".join(sources[:3]) if sources else "Web search results"
                        
                        return AGHResponse(
                            answer=f"{answer}\n\n🌐 *This answer is based on web search for AGH University regulations.*",
                            sources=sources_text,
                            trust_score=0.7,  # Higher trust for web results when explicitly requested
                            warning=None,
                            section_refs=[],
                            language="en",
                            tokens=total_tokens,
                            processing_time=time_module.time() - start_time,
                            sources_type="web"  # Mark as web sources
                        )
                except Exception as e:
                    logger.error(f"Web search failed: {e}")
                    logger.info("🔄 Falling back to document search...")
            
            if not indices:
                # No relevant documents found - suggest web search
                if enable_web_search:
                    logger.info("🌐 No relevant AGH documents found, searching web for AGH regulations...")
                    try:
                        from app.services.enhanced_web_search import EnhancedWebSearchService
                        web_search = EnhancedWebSearchService()
                        
                        # Focus search specifically on AGH University of Krakow
                        agh_search_query = f"AGH University of Science and Technology Krakow regulations {question}"
                        search_results = web_search.search_and_extract(agh_search_query, max_results=3)
                        
                        if search_results:
                            # Build web search answer focused on AGH
                            web_content = []
                            sources = []
                            for result in search_results[:3]:
                                web_content.append(f"• {result.get('snippet', '')}")
                                if result.get('url'):
                                    sources.append(result['url'])
                            
                            # Create AGH-focused web search answer with conciseness instructions
                            web_prompt = f"""Question about AGH University of Science and Technology Krakow: {question}

📋 RESPONSE FORMAT:
- Keep your answer CONCISE and FOCUSED (2-3 paragraphs maximum)
- Extract only the ESSENTIAL information that directly answers the question
- Use bullet points for lists to improve readability
- Be direct and to-the-point

Based on web search results about AGH regulations:

{chr(10).join(web_content)}

Please provide a concise, helpful answer specifically about AGH University regulations based on these web search results. If the results don't contain AGH-specific information, clearly state that."""
                            
                            answer, tokens = self._generate_answer(web_prompt)
                            sources_text = ", ".join(sources[:3]) if sources else "Web search results"
                            
                            return AGHResponse(
                                answer=f"{answer}\n\n🌐 *This answer is based on web search for AGH University regulations since no relevant documents were found in our database.*",
                                sources=sources_text,
                                trust_score=0.6,  # Lower trust for web results
                                warning="Answer based on web search for AGH regulations - not from internal documents",
                                section_refs=[],
                                language="en",
                                tokens=tokens,
                                processing_time=time_module.time() - start_time,
                                sources_type="web"
                            )
                    except Exception as e:
                        logger.error(f"Web search fallback failed: {e}")
                
                return AGHResponse(
                    answer="No relevant AGH regulations found for your question. To search the web for AGH University information, try enabling web search or adding 'search' to your question.",
                    sources="N/A",
                    trust_score=0.0,
                    warning="No relevant AGH documents found - enable web search to search online",
                    section_refs=[],
                    language="en",
                    tokens=input_tokens,
                    processing_time=time_module.time() - start_time,
                    sources_type="document"
                )
            
            # Prepare chunks and metadata
            chunks = []
            metadata = []
            for i in indices:
                row = self.df.iloc[i]
                title = row.get('Title', '')
                content = row.get('Content', '')
                section_number = self._extract_section_number(title)
                
                chunks.append(f"[{title}]\n{content}")
                metadata.append({
                    "section": section_number,
                    "title": title,
                    "content": content
                })
            
            # Build prompt and generate answer
            prompt, used_chunks, used_metadata = self._build_prompt(chunks, metadata, question, user_profile)
            answer, tokens_generated = self._generate_answer(prompt)
            total_tokens = input_tokens + tokens_generated
            
            # Post-process answer to fix known incorrect information from Google Sheets
            answer = self._fix_known_errors(answer)
            
            # Extract section references from answer
            section_matches = re.findall(r'(?:§\s*|Section\s+)(\d+(?:\.\d+)?)(?![^\n]*semester)', answer)
            unique_refs = sorted(set(section_matches))
            
            # Build sources from used documents (not web search) with clear identification
            used_sections = []
            for meta in used_metadata:
                section_ref = meta['section'] if meta['section'] != "N/A" else "General"
                used_sections.append(f"{meta['title'].strip()} (§{section_ref})")
            
            # Format sources properly - showing actual document sources used (AGH Documents)
            if used_sections:
                sources = ", ".join(sorted(set(used_sections)))
                sources_type = "document"  # Mark as document sources
            else:
                sources = "AGH University Regulations Database"
                sources_type = "document"
            
            # Calculate trust score
            trust_score = self._calculate_trust_score(question, answer, [meta['content'] for meta in used_metadata])
            
            # Check for warnings
            warning = None
            if self._is_low_quality_answer(question, answer) or trust_score < 0.65:
                warning = "Warning: This answer may be incomplete or off-topic."
            elif not used_metadata:  # Check if no documents were actually used
                warning = "Warning: This answer contains no cited regulation sections."
            
            # Check relevance for very low scores - but be more lenient
            if trust_score < 0.3 and not indices:  # Only reject if NO chunks found AND very low score
                relevance_prompt = f"Is this question about university study regulations, academic rules, student rights, or educational policies? Answer only 'Yes' or 'No'.\n\nQuestion: {question}"
                relevance_answer, _ = self._generate_answer(relevance_prompt)
                
                if 'no' in relevance_answer.lower():
                    return AGHResponse(
                        answer="This question is not related to AGH regulations.",
                        sources="N/A",
                        trust_score=0.0,
                        warning=None,
                        section_refs=[],
                        language="en",
                        tokens=total_tokens,
                        processing_time=time_module.time() - start_time,
                        sources_type="document"
                    )
            
            return AGHResponse(
                answer=answer,
                sources=sources,
                trust_score=trust_score,
                warning=warning,
                section_refs=unique_refs,
                language="en",
                tokens=total_tokens,
                processing_time=time_module.time() - start_time,
                sources_type=sources_type  # Pass the sources type
            )
            
        except Exception as e:
            logger.error(f"❌ AGH question answering failed: {e}")
            return AGHResponse(
                answer="Sorry, there was an error processing your question.",
                sources="N/A",
                trust_score=0.0,
                warning="Processing error",
                section_refs=[],
                language="en",
                tokens=input_tokens,
                processing_time=time_module.time() - start_time,
                sources_type="document"
            )

# Global instance
agh_rag_service = AGHRAGService()
