# Student Hub App Functions

A comprehensive educational automation tool that integrates Canvas LMS, Google Docs, and AI services to help students manage their academic work more efficiently.

## Features

### Canvas Integration
- Fetch course information and assignments
- Get real-time grades and due dates
- Access professor information
- Track academic progress
- Get student's current academic year
- Retrieve user's full name

### Google Docs Automation
- Automatically create formatted documents
- Organize files by course in Google Drive
- Create proper headers and formatting
- Smart folder management
- Move files between folders
- Create class-specific folders
- Save and track folder information
- Interactive homework document creation
- Automatic assignment organization

### AI Services
- Convert lecture speech to text
- Generate lecture summaries
- Get AI assistance with homework
- Receive personalized YouTube video recommendations
- Smart content generation
- Transcribe spoken lectures
- Generate text summaries
- Recommend educational videos

## Available Functions

### Canvas Service
```python
from hub_app.services.canvas_service import CanvasService

canvas = CanvasService(api_token, canvas_url)
canvas.get_user_name()              # Get current user's full name
canvas.get_classes()                # Get list of active classes
canvas.get_course_professor(id)     # Get professor name for a course
canvas.get_grades(course_id)        # Get grades for a specific course
canvas.get_current_assignments(id)  # Get current assignments for a course
canvas.get_current_year()           # Get student's academic year
```

### Docs Service
```python
from hub_app.services.docs_service import DocsService
docs = DocsService(credentials_path, folder_ids_path)
docs.create_document(title) # Create new Google Doc
docs.update_document(doc_id, name, professor, class_name) # Update doc with formatting and header
docs.move_to_folder(file_id, folder_id) # Move file to specific folder
docs.create_class_folders(parent_id, classes) # Create folders for classes
docs.create_homework_document(canvas_service) # Create interactive homework documen
```

### AI Service
```python
from hub_app.services.ai_service import AIService

ai = AIService()
ai.transcribe_speech(duration)      # Convert speech to text
ai.summarize_text(text)            # Generate text summary
ai.recommend_videos(prompt)         # Get YouTube video recommendations
ai.create_lecture_summary(duration) # Create summary from spoken lecture
ai.get_homework_help(...)          # Get AI assistance with homework
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hub_app.git
   cd hub_app
   ```

2. Install the dependencies:
   ```bash
   pip install -e .
   ```

## Usage

### Canvas Service
```python
from hub_app.services.canvas_service import CanvasService

canvas = CanvasService(api_token, canvas_url)
classes = canvas.get_classes()
assignments = canvas.get_current_assignments(course_id)
```

### Docs Service
```python
from hub_app.services.docs_service import DocsService

docs = DocsService(credentials_path, folder_ids_path)
doc = docs.create_document("Assignment Title")
docs.update_document(doc_id, name, professor, class_name)
```

### AI Service
```python
from hub_app.services.ai_service import AIService

ai = AIService()
summary = ai.create_lecture_summary(duration=300)  # 5 minutes
videos = ai.recommend_videos("Python tutorials")
homework_help = ai.get_homework_help(assignment_name, course_name, description)
```

## Required API Keys

1. Canvas LMS API Token
   - Go to Canvas Account Settings
   - Generate New Access Token

2. Google Cloud API Credentials
   - Create project in Google Cloud Console
   - Enable Google Docs and Drive APIs
   - Create OAuth 2.0 credentials

3. Gemini API Key
   - Sign up for Google AI Studio
   - Generate API key

4. YouTube Data API Key
   - Enable YouTube Data API in Google Cloud Console
   - Create API key

## Configuration

1. Create a `credentials.json` file from Google Cloud Console
2. Run the application once to generate `token.pickle`
3. Update `.env` with all required API keys
4. Configure folder paths in `config/settings.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Dependencies

- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- google-generativeai
- speech_recognition
- canvasapi
- python-dotenv
- pandas
- requests

## Acknowledgments

- Canvas LMS API
- Google Cloud Platform
- Google AI (Gemini)
- YouTube Data API

## Support

For support, please open an issue in the GitHub repository or contact [iammorechad@gmail.com].