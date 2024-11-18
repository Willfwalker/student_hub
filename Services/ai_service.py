import google.generativeai as genai
from typing import Optional, List
from googleapiclient.discovery import build
import speech_recognition as sr
from config.settings import GEMINI_API_KEY, YOUTUBE_API_KEY
from PIL import Image

class AIService:
    def __init__(self):
        self._configure_gemini()
        self.model = genai.GenerativeModel('gemini-pro')
        self.recognizer = sr.Recognizer()

    def _configure_gemini(self):
        """Configure Gemini AI with API key."""
        genai.configure(api_key=GEMINI_API_KEY)

    def transcribe_speech(self, duration: int) -> Optional[str]:
        """Convert speech to text."""
        try:
            with sr.Microphone() as source:
                print("Starting transcription...")  # Debug log
                print(f"Recording duration: {duration} seconds")  # Debug log
                
                # Adjust for ambient noise
                print("Adjusting for ambient noise...")  # Debug log
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                print("Listening... Speak now")  # Debug log
                audio = self.recognizer.listen(
                    source, 
                    timeout=duration,  # Add timeout
                    phrase_time_limit=duration
                )
                
                print("Audio captured, processing...")  # Debug log
                
                # Try services in order of reliability
                try:
                    # Try Google Web Speech API first
                    text = self.recognizer.recognize_google(audio)
                    return text
                except sr.UnknownValueError:
                    try:
                        # Fallback to Sphinx (offline)
                        text = self.recognizer.recognize_sphinx(audio)
                        return text
                    except:
                        # Could add more fallback services here
                        return None
                    
        except Exception as e:
            print(f"Unexpected error during transcription: {e}")
            return None

    def summarize_text(self, text: str) -> Optional[str]:
        """Generate a summary of the provided text."""
        try:
            if not text or not text.strip():
                raise ValueError("Empty text provided")
            
            prompt = f"""Please provide a concise summary of the following text, 
            highlighting the key points and main ideas:
            
            {text}"""
            
            response = self.model.generate_content(prompt)
            
            if not response:
                raise Exception("No response received from Gemini API")
            
            if not response.text:
                raise Exception("Empty response received from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}")

    def recommend_videos(self, prompt: str, max_results: int = 3) -> Optional[List[dict]]:
        """Recommend YouTube videos based on a topic."""
        try:
            print(f"Starting video search for prompt: {prompt}")  # Debug log
            
            # Search YouTube directly with the prompt
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            
            response = youtube.search().list(
                part="snippet",
                maxResults=max_results,
                q=prompt,
                type="video",
                relevanceLanguage="en",
                videoEmbeddable="true"
            ).execute()
            
            # Format the videos
            videos = []
            for item in response['items']:
                video = {
                    'title': item['snippet']['title'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'description': item['snippet']['description']
                }
                videos.append(video)
                print(f"Found video: {video['title']}")  # Debug log
            
            return videos
            
        except Exception as e:
            print(f"Error recommending videos: {e}")
            return None

    def create_lecture_summary(self, duration: int) -> Optional[str]:
        """Create a summary from spoken lecture."""
        try:
            print(f"Starting lecture summary for duration: {duration}")  # Debug log
            
            text = self.transcribe_speech(duration)
            print(f"Transcribed text: {text}")  # Debug log
            
            if not text:
                raise ValueError("No transcription available - speech not detected or understood")
            
            summary = self.summarize_text(text)
            print(f"Generated summary: {summary}")  # Debug log
            
            return summary
            
        except Exception as e:
            print(f"Error in create_lecture_summary: {str(e)}")
            raise Exception(f"Failed to create summary: {str(e)}")

    def get_homework_help(self, assignment_name: str, course_name: str, 
                         description: str) -> Optional[str]:
        """Get AI assistance for homework."""
        try:
            prompt = f"""Do this assignment for my {course_name} class: {assignment_name}
            Assignment Description: {description}
            
            Please answer like a college student, following these rules:
            - Use complete sentences and clear language
            - Write in paragraph form with proper indentation
            - Use double spacing
            - Include only the assignment content
            - No headers, footers, or special formatting
            
            Format the response as plain text without any Markdown or special characters."""
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error getting homework help: {e}")
            return None    

    def get_ai_response(self, prompt: str) -> Optional[str]:
        """Get a response from AI for any given prompt."""
        try:
            if not prompt or not prompt.strip():
                raise ValueError("Empty prompt provided")
            
            response = self.model.generate_content(prompt)
            
            if not response:
                raise Exception("No response received from Gemini API")
            
            if not response.text:
                raise Exception("Empty response received from Gemini API")
            
            # Clean up the response by removing asterisks
            cleaned_response = response.text.strip().replace('*', '')
            return cleaned_response
            
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            return None

    def generate_image(self, prompt: str, 
                      height: int = 1024, 
                      width: int = 1024,
                      seed: Optional[int] = None) -> Optional[Image.Image]:
        """Return the default icon."""
        try:
            return Image.open("@default_icon.png")
        except Exception as e:
            print(f"Error loading default icon: {str(e)}")
            return None

    def create_video_search_prompt(self, assignment_name: str, description: str) -> Optional[str]:
        """Create an optimized YouTube search prompt from assignment details."""
        try:
            if not assignment_name or not description:
                print("Missing assignment name or description")
                return None
            
            # Clean and validate inputs
            assignment_name = str(assignment_name).strip()
            description = str(description).strip()
            
            prompt = f"""Given this assignment:
            Title: {assignment_name}
            Description: {description}

            Create a concise, focused YouTube search query that will find educational videos 
            explaining the core concepts needed to complete this assignment. 
            The query should:
            - Be 2-3 key phrases
            - Focus on the main topic or skill needed
            - Use common educational terminology
            - Exclude assignment-specific details
            
            Return only the search query, no other text."""
            
            try:
                response = self.model.generate_content(prompt)
                
                if not response:
                    print("No response received from Gemini API")
                    return None
                    
                if not hasattr(response, 'text'):
                    print("Response missing text attribute")
                    return None
                    
                text = response.text
                if not text or not isinstance(text, str):
                    print("Invalid response text")
                    return None
                    
                # Clean up and format the response
                search_query = text.strip().replace('\n', ' ')
                print(f"Generated search query: {search_query}")  # Debug log
                return search_query
                
            except AttributeError as e:
                print(f"Attribute error with Gemini response: {e}")
                return None
                
        except Exception as e:
            print(f"Error creating video search prompt: {e}")
            return None
