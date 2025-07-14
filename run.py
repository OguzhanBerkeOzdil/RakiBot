#!/usr/bin/env python3
"""
RakıBot AI Assistant Runner
Main application launcher with environment setup and Flask server management
Developed by Oğuzhan Berke Özdil
"""

import os
import sys
import logging
import webbrowser
import threading
import time
from pathlib import Path

# OPTIONAL: Uncomment the line below if you want to use external APIs for enhanced features
# Currently using Ollama for fully local operation - no external API dependencies required
# os.environ['GOOGLE_API_KEY'] = "your_api_key_here"  # You can add your API key here if needed

# Add the project root to Python path for proper module imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Configure application logging with file and console output"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler('app.log', encoding='utf-8')  # File logging
        ]
    )

def check_environment():
    """
    Check if required environment variables and files exist
    Load configuration from .env file if available
    """
    os.chdir(project_root)
    
    # Load .env file if it exists for environment configuration
    env_file = Path('.env')
    if env_file.exists():
        print("Loading environment from .env file")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    else:
        print("Warning: .env file not found")
    
    return True

def open_browser(url, delay=2):
    """
    Open web browser automatically after Flask server starts
    Args:
        url: Target URL to open
        delay: Seconds to wait before opening (allows server startup)
    """
    time.sleep(delay)
    try:
        webbrowser.open(url)
        print(f"Browser opened: {url}")
    except Exception as e:
        print(f"Failed to open browser: {e}")

def main():
    """
    Main application entry point
    Initializes logging, loads Flask app, and starts the web server
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        print("RakıBot AI Assistant Starting...")
        print("=" * 50)
        
        if not check_environment():
            sys.exit(1)
        
        # Import and create the Flask application instance
        try:
            from app.main import create_app
            app = create_app()
            logger.info("RakıBot application initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import app: {e}")
            sys.exit(1)
        
        # Development settings
        debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))
        
        url = f"http://{host}:{port}"
        
        print(f"Server: {url}")
        print(f"Debug mode: {debug}")
        print(f"Access at: {url}")
        print("=" * 50)
        print()
        print("Browser will open automatically...")
        print("Press Ctrl+C to stop")
        print()
        
        # Open browser in a separate thread
        browser_thread = threading.Thread(target=open_browser, args=(url,))
        browser_thread.daemon = True
        browser_thread.start()
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\nRakıBot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start RakıBot: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
