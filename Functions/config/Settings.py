import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys and Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
CANVAS_API_TOKEN = os.getenv('CANVAS_API_TOKEN')
CANVAS_URL = os.getenv('CANVAS_URL')

# Google API Configuration
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')