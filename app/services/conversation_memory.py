"""
Conversation Memory Service
Manages chat history, context tracking, and user preference learning
for enhanced conversational continuity and personalization
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ConversationMessage:
    """Individual message container with metadata and timestamp"""
    role: str  # 'user' or 'assistant' - message originator
    content: str  # Message text content
    timestamp: datetime  # When the message was created
    metadata: Dict[str, Any]  # Additional context (confidence, sources, etc.)

class ConversationMemory:
    """
    Manages conversation history and context for intelligent responses
    Tracks topics, preferences, and maintains conversation flow
    """
    
    def __init__(self, max_messages: int = 50, context_window: int = 10):
        """
        Initialize conversation memory with configurable limits
        Args:
            max_messages: Maximum messages to retain in memory
            context_window: Number of recent messages to use for context
        """
        self.max_messages = max_messages      # Memory capacity limit
        self.context_window = context_window  # Active context size
        self.messages: List[ConversationMessage] = []  # Message history
        self.session_topics: List[str] = []   # Detected conversation topics
        self.user_preferences: Dict[str, Any] = {}  # Learned user preferences
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to conversation history with automatic topic extraction
        Args:
            role: 'user' or 'assistant' indicating message source
            content: The actual message text
            metadata: Optional context data (confidence scores, sources, etc.)
        """
        if metadata is None:
            metadata = {}
            
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.messages.append(message)
        
        # Keep only last max_messages to prevent memory overflow
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
        # Extract topics from user messages for context building
        if role == 'user':
            self._extract_topics(content)
            
        logger.debug(f"Added {role} message to conversation memory")
    
    def get_recent_context(self, include_current: bool = False) -> str:
        """Get recent conversation context as a string"""
        if not self.messages:
            return ""
            
        recent_messages = self.messages[-self.context_window:]
        if not include_current and recent_messages:
            recent_messages = recent_messages[:-1]
            
        context_parts = []
        for msg in recent_messages:
            role_prefix = "👤 Kullanıcı" if msg.role == 'user' else "🤖 Asistan"
            context_parts.append(f"{role_prefix}: {msg.content[:200]}...")
            
        return "\n".join(context_parts)
    
    def get_related_topics(self, current_question: str) -> List[str]:
        """Find topics related to current question"""
        current_lower = current_question.lower()
        related = []
        
        # Check recent topics
        for topic in self.session_topics[-10:]:  # Last 10 topics
            topic_words = topic.lower().split()
            question_words = current_lower.split()
            
            # Simple word overlap detection
            overlap = set(topic_words) & set(question_words)
            if len(overlap) >= 2:
                related.append(topic)
                
        return related
    
    def has_topic_context(self, topic: str) -> bool:
        """Check if topic has been discussed recently"""
        topic_lower = topic.lower()
        for message in self.messages[-5:]:  # Last 5 messages
            if topic_lower in message.content.lower():
                return True
        return False
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation so far"""
        if not self.messages:
            return "Yeni bir sohbet başlıyor."
            
        user_messages = [msg for msg in self.messages if msg.role == 'user']
        if not user_messages:
            return "Henüz kullanıcı sorusu yok."
            
        topics = list(set(self.session_topics[-5:]))  # Last 5 unique topics
        
        summary = f"Bu sohbette şu konular konuşuldu: {', '.join(topics) if topics else 'çeşitli konular'}"
        summary += f" Toplam {len(user_messages)} soru soruldu."
        
        return summary
    
    def _extract_topics(self, content: str):
        """Extract topics from user message"""
        content_lower = content.lower()
        
        # Geographic topics
        geographic_terms = ['nerede', 'nerededir', 'hangi', 'konum', 'yer', 'şehir', 'il', 'ülke']
        for term in geographic_terms:
            if term in content_lower:
                # Extract the subject being asked about
                words = content.split()
                for i, word in enumerate(words):
                    if term in word.lower() and i > 0:
                        subject = words[i-1]
                        self.session_topics.append(f"{subject} konumu")
                        break
        
        # Named entities (simple extraction)
        words = content.split()
        for word in words:
            if len(word) > 3 and word[0].isupper():
                self.session_topics.append(word)
        
        # Keep only last 20 topics
        if len(self.session_topics) > 20:
            self.session_topics = self.session_topics[-20:]
    
    def is_follow_up_question(self, question: str) -> bool:
        """Detect if this is a follow-up question"""
        follow_up_indicators = [
            'peki', 'o zaman', 'başka', 'daha', 'ayrıca', 'bir de', 
            'onun', 'bunun', 'şunun', 'orada', 'burada', 'böyle',
            'hayır', 'evet', 'tamam', 'anladım'
        ]
        
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in follow_up_indicators)
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.messages.clear()
        self.session_topics.clear()
        self.user_preferences.clear()
        logger.info("Conversation memory cleared")

# Global conversation memory instance
conversation_memory = ConversationMemory()
