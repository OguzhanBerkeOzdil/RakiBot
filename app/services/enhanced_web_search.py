"""
Enhanced Web Search Service - Real Working Implementation
Fixes all web search issues and provides actual results
"""

import logging
import requests
import time
import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup, Tag
from urllib.parse import quote_plus, urljoin, urlparse
import random

logger = logging.getLogger(__name__)

class EnhancedWebSearchService:
    """
    Enhanced Web Search that actually works
    - Multiple search engines
    - Real content extraction
    - Smart result filtering
    - Proper error handling
    """
    
    def __init__(self, cache_dir="web_cache"):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        
        # Realistic user agents to avoid blocking
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Security and Quality Filters
        self.trusted_domains = {
            # Official sites
            'youtube.com', 'youtu.be', 'google.com', 'microsoft.com', 'apple.com',
            # News and media
            'bbc.com', 'cnn.com', 'reuters.com', 'ap.org', 'bloomberg.com',
            # Educational
            'wikipedia.org', 'britannica.com', 'khanacademy.org', 'coursera.org',
            'mit.edu', 'harvard.edu', 'stanford.edu', 'agh.edu.pl',
            # Tech and programming
            'github.com', 'stackoverflow.com', 'mozilla.org', 'w3.org',
            # Turkish sites
            'tdk.gov.tr', 'yok.gov.tr', 'meb.gov.tr', 'hurriyet.com.tr',
            'cumhuriyet.com.tr', 'haberturk.com', 'ntv.com.tr'
        }
        
        self.blocked_domains = {
            # Adult content
            'pornhub.com', 'xvideos.com', 'xhamster.com', 'redtube.com',
            'youporn.com', 'tube8.com', 'pornzog.com', 'camsweb.net',
            'chaturbate.com', 'livejasmin.com', 'stripchat.com',
            'xnxx.com', 'brazzers.com', 'spankbang.com', 'eporner.com',
            'tnaflix.com', 'drtuber.com', 'sexvid.xxx', 'motherless.com',
            # Gambling
            'bet365.com', 'betway.com', 'pokerstars.com', '1xbet.com',
            'bingo.com', 'casino.com', 'williamhill.com', 'unibet.com',
            'ladbrokes.com', 'bwin.com', 'betfair.com', 'partypoker.com',
            # Malware/suspicious
            'bit.ly', 'tinyurl.com', 'shorturl.com', 'goo.gl',
            'ow.ly', 't.co', 'tiny.cc', 'is.gd', 'buff.ly',
            # File sharing (potential virus)
            'mediafire.com', 'rapidshare.com', 'megaupload.com',
            'uploaded.net', 'turbobit.net', 'nitroflare.com',
            'zippyshare.com', '4shared.com', 'filecrop.com',
            # Phishing/scam sites
            'phishing-site.com', 'fake-bank.net', 'scam-alert.org',
            'virus-alert.net', 'malware-download.com', 'trojan-virus.net',
            # Ad/redirect sites
            'popads.net', 'adsystem.com', 'clickfunnels.com',
            'redirect-ads.net', 'popup-ads.com', 'banner-ads.org'
        }
        
        self.adult_keywords = {
            'porn', 'sex', 'adult', 'xxx', 'nude', 'naked', 'erotic',
            'webcam', 'cam', 'live', 'chat', 'model', 'escort',
            'milf', 'teen', 'anal', 'oral', 'fetish', 'bdsm',
            'lesbian', 'gay', 'bisexual', 'trans', 'shemale',
            'masturbation', 'orgasm', 'climax', 'pussy', 'dick',
            'cock', 'penis', 'vagina', 'breast', 'boobs', 'tits',
            'ass', 'butt', 'booty', 'strip', 'sexy', 'hot',
            'dating', 'hookup', 'affair', 'swinger', 'threesome'
        }
        
        # Create cache directory
        import os
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info("🌐 Enhanced Web Search Service initialized with security filters")
    
    def search_multiple_engines(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search multiple engines and combine results"""
        all_results = []
        
        # Try DuckDuckGo first (most reliable)
        try:
            ddg_results = self.search_duckduckgo(query, max_results // 2)
            all_results.extend(ddg_results)
            logger.info(f"🦆 DuckDuckGo: {len(ddg_results)} results")
        except Exception as e:
            logger.warning(f"DuckDuckGo failed: {e}")
        
        # Try Bing as backup
        try:
            bing_results = self.search_bing(query, max_results // 2)
            all_results.extend(bing_results)
            logger.info(f"🅱️ Bing: {len(bing_results)} results")
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        logger.info(f"🔍 Total unique results: {len(unique_results)}")
        return unique_results[:max_results]
    
    def search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search DuckDuckGo with improved parsing"""
        try:
            # DuckDuckGo instant answer API (for some queries)
            api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            
            api_response = self.session.get(api_url, timeout=10)
            if api_response.status_code == 200:
                data = api_response.json()
                
                results = []
                
                # Check for instant answer
                if data.get('AbstractText'):
                    results.append({
                        'title': data.get('Heading', 'DuckDuckGo Instant Answer'),
                        'url': data.get('AbstractURL', ''),
                        'snippet': data.get('AbstractText', ''),
                        'content': data.get('AbstractText', ''),
                        'source': 'duckduckgo_instant'
                    })
                
                # Check for related topics
                for topic in data.get('RelatedTopics', [])[:5]:
                    if isinstance(topic, dict) and topic.get('Text'):
                        results.append({
                            'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                            'url': topic.get('FirstURL', ''),
                            'snippet': topic.get('Text', ''),
                            'content': topic.get('Text', ''),
                            'source': 'duckduckgo_related'
                        })
                
                if results:
                    logger.info(f"🦆 DuckDuckGo API: {len(results)} instant results")
                    return results
            
            # Fallback to HTML scraping if API doesn't return enough
            return self.search_duckduckgo_html(query, max_results)
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def search_duckduckgo_html(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search DuckDuckGo by scraping HTML"""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search result containers
            result_containers = soup.find_all('div', class_='result')
            
            for container in result_containers[:max_results]:
                try:
                    # Extract title and URL
                    if not isinstance(container, Tag):
                        continue
                    
                    title_link = container.find('a', {'class': 'result__a'})
                    if not title_link or not isinstance(title_link, Tag):
                        continue
                    
                    title = title_link.get_text(strip=True)
                    url_attr = title_link.get('href')
                    url = str(url_attr) if url_attr else ''
                    
                    # Fix DuckDuckGo redirect URLs
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    # Extract snippet
                    snippet_elem = container.find('a', {'class': 'result__snippet'})
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem and isinstance(snippet_elem, Tag) else ''
                    
                    if title and url:
                        # Try to get more content by fetching the page
                        content = self.extract_page_content(url)
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'content': content[:1000] if content else snippet,
                            'source': 'duckduckgo_html'
                        })
                
                except Exception as e:
                    logger.warning(f"Error parsing DuckDuckGo result: {e}")
                    continue
            
            logger.info(f"🦆 DuckDuckGo HTML: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo HTML search failed: {e}")
            return []
    
    def search_bing(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Bing as backup"""
        try:
            search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search results
            result_containers = soup.find_all('li', class_='b_algo')
            
            for container in result_containers[:max_results]:
                try:
                    # Extract title and URL
                    if not isinstance(container, Tag):
                        continue
                    
                    title_elem = container.find('h2')
                    if not title_elem or not isinstance(title_elem, Tag):
                        continue
                    
                    title_link = title_elem.find('a')
                    if not title_link or not isinstance(title_link, Tag):
                        continue
                    
                    title = title_link.get_text(strip=True)
                    url_attr = title_link.get('href')
                    url = str(url_attr) if url_attr else ''
                    
                    # Extract snippet
                    snippet_elem = container.find('div', {'class': 'b_caption'})
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem and isinstance(snippet_elem, Tag) else ''
                    
                    if title and url:
                        content = self.extract_page_content(url)
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'content': content[:1000] if content else snippet,
                            'source': 'bing'
                        })
                
                except Exception as e:
                    logger.warning(f"Error parsing Bing result: {e}")
                    continue
            
            logger.info(f"🅱️ Bing: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []
    
    def extract_page_content(self, url: str) -> Optional[str]:
        """Extract meaningful content from a webpage"""
        try:
            # Fix DuckDuckGo redirect URLs
            if url.startswith('//duckduckgo.com/l/'):
                # Extract the actual URL from DuckDuckGo redirect
                import urllib.parse
                if 'uddg=' in url:
                    actual_url = url.split('uddg=')[1].split('&')[0]
                    url = urllib.parse.unquote(actual_url)
                    logger.info(f"🔗 Extracted URL from DuckDuckGo redirect: {url}")
            
            # Add scheme if missing
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Check cache first
            cache_key = hashlib.md5(url.encode()).hexdigest()
            cache_file = f"{self.cache_dir}/{cache_key}.txt"
            
            import os
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Skip certain file types
            if any(url.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']):
                return None
            
            # Fetch page
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Extract main content
            content_selectors = [
                'main',
                'article', 
                '.content',
                '.main-content',
                '.post-content',
                '.entry-content',
                '#content',
                '#main'
            ]
            
            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
                
                # Clean up text
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)
                
                # Limit length
                if len(text) > 2000:
                    text = text[:2000] + "..."
                
                # Cache the result
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                except:
                    pass  # Cache write failure is not critical
                
                return text
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return None
    
    def search_and_extract(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """Enhanced search method with music/video link optimization and security filtering"""
        logger.info(f"🔍 Searching for: {query}")
        
        # Detect if this is a music/video search
        music_keywords = ["song", "music", "video", "youtube", "şarkı", "müzik", "klip", "band", "artist", "metallica", "unforgiven"]
        is_music_search = any(keyword.lower() in query.lower() for keyword in music_keywords)
        
        if is_music_search:
            logger.info("🎵 Detected music search - optimizing for music platforms")
            # For music searches, modify query to prioritize YouTube and music platforms
            music_query = f"{query} youtube OR spotify OR soundcloud"
            search_results = self.search_multiple_engines(music_query, max_results * 2)  # Get more to filter
            
            # Also try direct music query
            if len(search_results) < max_results:
                direct_results = self.search_multiple_engines(query, max_results)
                search_results.extend(direct_results)
        else:
            # Normal search - get extra results for filtering
            search_results = self.search_multiple_engines(query, max_results * 2)
        
        if not search_results:
            logger.warning("🚫 No search results found")
            return []
        
        # Apply security filtering first
        safe_results = self.filter_and_rank_results(search_results)
        
        if not safe_results:
            logger.warning("🚫 No safe results found after filtering")
            return []
        
        # Filter and enhance results
        enhanced_results = []
        for result in safe_results:
            # For music searches, prioritize working links
            if is_music_search:
                url = result.get('url', '')
                # Prioritize YouTube, Spotify, and other music platforms
                if any(platform in url.lower() for platform in ['youtube.com', 'youtu.be', 'spotify.com', 'soundcloud.com']):
                    # Ensure YouTube links are properly formatted
                    if 'youtube.com' in url or 'youtu.be' in url:
                        if not url.startswith('http'):
                            url = f"https://{url}"
                        result['url'] = url
                        enhanced_results.insert(0, result)  # Prioritize music links
                        continue
            
            # Skip if no meaningful content for non-music searches
            if not is_music_search and (not result.get('content') or len(result['content']) < 50):
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(query, result)
            result['relevance_score'] = relevance_score
            
            # Only keep relevant results
            if relevance_score > 0.3:
                enhanced_results.append(result)
        
        # Sort by combined trust and relevance score
        enhanced_results.sort(key=lambda x: (x.get('trust_score', 0.5) * 0.6 + x.get('relevance_score', 0) * 0.4), reverse=True)
        
        logger.info(f"✅ Enhanced search complete: {len(enhanced_results)} safe and relevant results")
        return enhanced_results[:max_results]
    
    def _calculate_relevance(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate relevance score for a search result"""
        query_terms = query.lower().split()
        
        title = result.get('title', '').lower()
        content = result.get('content', '').lower()
        snippet = result.get('snippet', '').lower()
        
        score = 0.0
        
        # Title matches (high weight)
        for term in query_terms:
            if term in title:
                score += 0.3
        
        # Content matches (medium weight)
        for term in query_terms:
            if term in content:
                score += 0.2
        
        # Snippet matches (medium weight)
        for term in query_terms:
            if term in snippet:
                score += 0.2
        
        # Bonus for exact phrase match
        if query.lower() in content:
            score += 0.3
        
        # Content length bonus (prefer substantial content)
        content_length = len(result.get('content', ''))
        if content_length > 500:
            score += 0.1
        elif content_length > 200:
            score += 0.05
        
        return min(score, 1.0)
    
    def is_safe_url(self, url: str, title: str = "", description: str = "") -> bool:
        """Check if URL is safe and appropriate"""
        try:
            # Parse URL
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check blocked domains
            for blocked in self.blocked_domains:
                if blocked in domain:
                    logger.warning(f"🚫 Blocked domain detected: {domain}")
                    return False
            
            # Check for adult content in URL, title, or description
            content_text = f"{url} {title} {description}".lower()
            for keyword in self.adult_keywords:
                if keyword in content_text:
                    logger.warning(f"🚫 Adult content keyword detected: {keyword}")
                    return False
            
            # Prefer trusted domains
            for trusted in self.trusted_domains:
                if trusted in domain:
                    logger.info(f"✅ Trusted domain: {domain}")
                    return True
            
            # Check for suspicious patterns
            if len(domain.split('.')) > 3:  # Too many subdomains
                logger.warning(f"🚫 Suspicious domain structure: {domain}")
                return False
            
            # Allow other domains but with lower priority
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking URL safety: {e}")
            return False
    
    def filter_and_rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter unsafe content and rank by trustworthiness"""
        safe_results = []
        
        for result in results:
            if self.is_safe_url(result.get('url', ''), result.get('title', ''), result.get('snippet', '')):
                # Add trust score
                domain = urlparse(result.get('url', '')).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Higher score for trusted domains
                trust_score = 0.5  # Default
                for trusted in self.trusted_domains:
                    if trusted in domain:
                        trust_score = 1.0
                        break
                
                result['trust_score'] = trust_score
                safe_results.append(result)
            else:
                logger.warning(f"🚫 Filtered unsafe result: {result.get('url', '')[:50]}...")
        
        # Sort by trust score (highest first)
        safe_results.sort(key=lambda x: x.get('trust_score', 0), reverse=True)
        
        logger.info(f"🛡️ Filtered results: {len(safe_results)} safe out of {len(results)} total")
        return safe_results
