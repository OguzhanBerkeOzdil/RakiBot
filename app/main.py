"""
Modern Flask Application with Dual AI System - RakıBot
- Normal Mode: Gemma 3 (Ollama) + Web Search  
- AGH Mode: Document-based RAG with regulations
Developed by Oğuzhan Berke Özdil
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template, session
from werkzeug.exceptions import HTTPException

from app.config.config import config
from app.core.advanced_rag_engine import AdvancedAtlasRAGEngine
from app.services.agh_rag_service import agh_rag_service
from app.services.enhanced_embedding_service import AdvancedEmbeddingService
from app.services.enhanced_web_search import EnhancedWebSearchService
from app.services.conversation_memory import conversation_memory

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.security.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.secret_key = config.security.secret_key
    
    # Global variables for chat settings
    app.config['CURRENT_CHAT_MODE'] = 'normal'  # 'normal' or 'agh'
    app.config['WEB_SEARCH_ENABLED'] = False  # Default to false - users can enable if needed
    
    # Initialize services
    logger.info("🚀 Initializing RakıBot AI Assistant...")
    
    try:
        # Initialize Normal RAG Engine (Gemma 3)
        app.config['NORMAL_RAG_ENGINE'] = AdvancedAtlasRAGEngine()
        logger.info("✅ Normal RAG Engine (Gemma 3) initialized")
        
        # Initialize AGH RAG Service
        # (agh_rag_service is already initialized as global instance)
        logger.info("✅ AGH RAG Service initialized")
        
        # Initialize enhanced services for multi-modal operation
        # Embedding service handles vector operations for document similarity
        app.config['EMBEDDING_SERVICE'] = AdvancedEmbeddingService()
        # Web search service provides real-time information retrieval
        app.config['WEB_SEARCH_SERVICE'] = EnhancedWebSearchService()
        
        logger.info("✅ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise
    
    @app.route('/')
    def index():
        """Main chat interface - serves the primary conversational UI"""
        return render_template('chat.html')
    
    @app.route('/health')
    def health_check():
        """
        Health check endpoint for monitoring system status
        Returns service availability and timestamp
        """
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "normal_rag": "online",
                "agh_rag": "online", 
                "web_search": "online"
            }
        })
    
    @app.route('/api/chat-mode', methods=['POST'])
    def set_chat_mode():
        """
        Switch between conversation modes
        - normal: General Gemma 3 conversation with web search
        - agh: Academic regulation-focused RAG system
        """
        try:
            data = request.get_json()
            mode = data.get('mode', 'normal')
            
            if mode not in ['normal', 'agh']:
                return jsonify({"success": False, "error": "Invalid mode"}), 400
            
            app.config['CURRENT_CHAT_MODE'] = mode
            logger.info(f"🔄 Chat mode set to: {mode}")
            
            return jsonify({"success": True, "chat_mode": mode})
            
        except Exception as e:
            logger.error(f"❌ Failed to set chat mode: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/get-chat-mode')
    def get_chat_mode():
        """Get current chat mode"""
        return jsonify({
            "success": True,
            "chat_mode": app.config.get('CURRENT_CHAT_MODE', 'normal')
        })
    
    @app.route('/api/get-web-search-status', methods=['GET'])
    def get_web_search_status():
        """Get current web search status"""
        return jsonify({
            "success": True,
            "web_search_enabled": app.config.get('WEB_SEARCH_ENABLED', False)
        })
    
    @app.route('/api/web-search-toggle', methods=['POST'])
    def toggle_web_search():
        """Toggle web search on/off"""
        try:
            data = request.get_json()
            enabled = data.get('enabled', True)
            
            app.config['WEB_SEARCH_ENABLED'] = enabled
            logger.info(f"🌐 Web search {'enabled' if enabled else 'disabled'}")
            
            return jsonify({"success": True, "web_search_enabled": enabled})
            
        except Exception as e:
            logger.error(f"❌ Failed to toggle web search: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/clear-conversation', methods=['POST'])
    def clear_conversation():
        """Clear conversation memory"""
        try:
            conversation_memory.clear_memory()
            logger.info("🧹 Conversation memory cleared")
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"❌ Failed to clear conversation: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Main chat endpoint"""
        start_time = datetime.now()
        
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            user_message = data.get('message', '').strip()
            enable_web_search = data.get('enable_web_search', app.config.get('WEB_SEARCH_ENABLED', True))
            
            if not user_message:
                return jsonify({"error": "Empty message"}), 400
            
            logger.info(f"💬 Processing message: {user_message[:100]}...")
            
            # Get current chat mode
            chat_mode = app.config.get('CURRENT_CHAT_MODE', 'normal')
            logger.info(f"🎯 Chat mode: {chat_mode}")
            
            # Process based on mode
            if chat_mode == 'agh':
                # AGH Mode - Use document-based RAG
                logger.info("🔧 Using AGH RAG mode")
                
                # Get user profile for adaptive responses (AGH mode doesn't use tone/dialect)
                user_profile = {
                    'gender': session.get('user_gender', '')
                }
                
                agh_response = agh_rag_service.answer_question(
                    user_message, 
                    enable_web_search=enable_web_search,
                    user_profile=user_profile
                )
                
                response_data = {
                    "answer": agh_response.answer,
                    "sources": agh_response.sources,
                    "sources_type": agh_response.sources_type,  # Add sources type for frontend
                    "confidence_score": agh_response.trust_score,
                    "chunks_used": len(agh_response.section_refs),
                    "chunk_quality": "🔧 AGH Document",
                    "response_time": f"{agh_response.processing_time:.2f}s",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "mode": "AGH_RAG",
                    "web_enhanced": enable_web_search,
                    "warning": agh_response.warning,
                    "section_refs": agh_response.section_refs,
                    "token_count": agh_response.tokens  # Input Token Count like original AGH expert
                }
                
            else:
                # Normal Mode - Use Gemma 3 RAG with Trakya dialect
                logger.info("🧠 Using Normal RAG mode (Gemma 3 + Trakya dialect)")
                normal_engine = app.config['NORMAL_RAG_ENGINE']
                
                # Get user profile for adaptive responses (includes tone for Trakya dialect)
                user_profile = {
                    'gender': session.get('user_gender', ''),
                    'tone': session.get('user_tone', 'friendly')
                }
                
                rag_response = normal_engine.process_question(
                    user_message,
                    enable_web_search=enable_web_search,
                    chat_mode=chat_mode,
                    user_profile=user_profile
                )
                
                response_data = {
                    "answer": rag_response.answer,
                    "sources": rag_response.sources,
                    "sources_type": rag_response.sources_type,  # Add sources type for frontend
                    "web_source_urls": rag_response.web_source_urls,  # Add actual web URLs
                    "confidence_score": rag_response.confidence_score,
                    "chunks_used": rag_response.chunks_used,
                    "chunk_quality": rag_response.chunk_quality,
                    "response_time": f"{rag_response.response_time:.2f}s",
                    "timestamp": rag_response.timestamp,
                    "mode": rag_response.mode,
                    "web_enhanced": rag_response.web_enhanced
                }
                
                # Debug log for Normal mode sources
                logger.info(f"🔍 Normal mode response debug:")
                logger.info(f"   sources: {rag_response.sources}")
                logger.info(f"   sources_type: {rag_response.sources_type}")
                logger.info(f"   web_source_urls: {rag_response.web_source_urls}")
                logger.info(f"   web_enhanced: {rag_response.web_enhanced}")
            
            # Add to conversation memory
            conversation_memory.add_message("user", user_message)
            conversation_memory.add_message("assistant", response_data["answer"])
            
            # Calculate total processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            response_data["total_processing_time"] = f"{processing_time:.2f}s"
            
            logger.info(f"✅ Response generated in {processing_time:.2f}s")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"❌ Chat processing failed: {e}", exc_info=True)
            return jsonify({
                "error": f"Sorry, there was an error processing your message: {str(e)}",
                "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                "sources": "",
                "confidence_score": 0.0,
                "chunks_used": 0,
                "chunk_quality": "❌ Error",
                "response_time": "0.00s",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "mode": "ERROR"
            }), 500
    
    @app.route('/api/user-tone', methods=['POST'])
    @app.route('/api/user-tone', methods=['POST'])
    def update_user_tone():
        """Update user tone/personality preference"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Store in session
            session['user_tone'] = data.get('tone', 'friendly')  # friendly, humorous, serious
            
            logger.info(f"🎭 User tone updated: {session.get('user_tone')}")
            
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"❌ Error updating user tone: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/user-profile', methods=['POST'])
    def update_user_profile():
        """Update user profile information"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Store in session (removed age completely)
            session['user_gender'] = data.get('gender', '')
            session['user_tone'] = data.get('tone', 'friendly')  # Added tone support
            
            logger.info(f"👤 User profile updated: gender={session.get('user_gender')}, tone={session.get('user_tone')}")
            
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"❌ Error updating user profile: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/agh-suggested-questions')
    def get_agh_suggested_questions():
        """Get suggested questions for AGH mode"""
        questions = [
            {
                "question": "What is the passing grade for exams?",
                "question_tr": "Sınavların geçme notu kaçtır?",
                "category": "grades"
            },
            {
                "question": "How are midterm and final exam grades calculated?",
                "question_tr": "Vize ve final notları nasıl hesaplanır?", 
                "category": "calculation"
            },
            {
                "question": "What are the attendance requirements?",
                "question_tr": "Devamsızlık kuralları nelerdir?",
                "category": "attendance"
            },
            {
                "question": "What happens if I exceed 30% absenteeism?",
                "question_tr": "30% devamsızlığı aşarsam ne olur?",
                "category": "attendance"
            },
            {
                "question": "What are student rights and responsibilities?",
                "question_tr": "Öğrenci hak ve sorumlulukları nelerdir?",
                "category": "rights"
            },
            {
                "question": "How can I appeal an exam grade?",
                "question_tr": "Sınav notuna nasıl itiraz edebilirim?",
                "category": "appeal"
            },
            {
                "question": "What are the discipline rules and penalties?",
                "question_tr": "Disiplin kuralları ve cezaları nelerdir?",
                "category": "discipline"
            },
            {
                "question": "What scholarship opportunities are available?",
                "question_tr": "Hangi burs imkanları mevcut?",
                "category": "scholarships"
            },
            {
                "question": "How do I transfer courses from another university?",
                "question_tr": "Başka üniversiteden ders nasıl transfer ederim?",
                "category": "transfer"
            },
            {
                "question": "What are the thesis and graduation requirements?",
                "question_tr": "Tez ve mezuniyet gereksinimleri nelerdir?",
                "category": "graduation"
            },
            {
                "question": "What IT services are available to students?",
                "question_tr": "Öğrencilere hangi IT hizmetleri sunuluyor?",
                "category": "technology"
            },
            {
                "question": "How do I get academic counseling support?",
                "question_tr": "Akademik danışmanlık desteği nasıl alırım?",
                "category": "support"
            }
        ]
        
        return jsonify({
            "success": True,
            "questions": questions
        })

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({"error": e.description}), e.code
    
    logger.info("🎉 RakıBot AI Assistant initialized successfully!")
    return app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    # Development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        threaded=True
    )
