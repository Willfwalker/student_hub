import google.generativeai as genai
from typing import Optional, List
from googleapiclient.discovery import build
import speech_recognition as sr
from config.settings import GEMINI_API_KEY, YOUTUBE_API_KEY

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
                
                # Try different speech recognition services
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"Transcription successful: {text}")  # Debug log
                    return text
                except sr.UnknownValueError:
                    print("Google Speech Recognition could not understand audio")
                    return None
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
                    return None
                
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
        except sr.WaitTimeoutError:
            print("No speech detected within timeout period")
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
        """Get a response from AI for any given prompt.
        
        Args:
            prompt (str): The user's prompt/question for the AI
            
        Returns:
            Optional[str]: The AI's response, or None if there's an error
        """
        try:
            if not prompt or not prompt.strip():
                raise ValueError("Empty prompt provided")
            
            response = self.model.generate_content(prompt)
            
            if not response:
                raise Exception("No response received from Gemini API")
            
            if not response.text:
                raise Exception("Empty response received from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            return None
