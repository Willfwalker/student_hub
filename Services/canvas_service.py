from typing import List, Dict, Optional
import requests
from canvasapi import Canvas
from datetime import datetime
from os import getenv
from dotenv import load_dotenv
from functools import lru_cache
import time

class CanvasService:
    def __init__(self):
        load_dotenv()
        self.api_token = getenv('CANVAS_API_TOKEN')
        if not self.api_token:
            raise ValueError("CANVAS_API_TOKEN not found in environment variables")
            
        self.canvas_url = getenv('CANVAS_URL')
        if not self.canvas_url:
            raise ValueError("CANVAS_URL not found in environment variables")
            
        self.canvas_url = self._format_canvas_url(self.canvas_url)
        self.canvas = Canvas(self.canvas_url, self.api_token)
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        self._cache = {}
        self.cache_duration = 300  # 5 minutes in seconds

    def _format_canvas_url(self, url: str) -> str:
        """Format Canvas URL consistently"""
        if not url.startswith('http'):
            url = f"https://{url}"
        return url.rstrip('/')

    def _get_cached_data(self, key):
        """Get cached data if it exists and is not expired"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None

    def _set_cached_data(self, key, data):
        """Cache data with current timestamp"""
        self._cache[key] = (data, time.time())

    @lru_cache(maxsize=32)
    def get_user_name(self) -> Optional[str]:
        """Get current user's full name (cached)"""
        endpoint = f"{self.canvas_url}/api/v1/users/self"
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json().get('name')
        except requests.exceptions.RequestException as e:
            print(f"Error getting user name: {str(e)}")
            return None

    def get_classes(self) -> List[Dict]:
        """Get user's active classes (cached)"""
        cache_key = 'classes'
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        endpoint = f"{self.canvas_url}/api/v1/courses"
        params = {
            'enrollment_state': 'active',
            'include[]': ['term', 'teachers'],
            'per_page': 100
        }
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()
            self._set_cached_data(cache_key, result)
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error fetching courses: {e}")
            return []

    def get_course_professor(self, course_id: int) -> Optional[str]:
        """Get professor name for a specific course"""
        try:
            course = self.canvas.get_course(course_id)
            teachers = course.get_users(enrollment_type=['teacher'])
            for teacher in teachers:
                return teacher.name
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    def get_grades(self, course_id: int) -> List[Dict]:
        """Get grades for a specific course"""
        endpoint = f"{self.canvas_url}/api/v1/courses/{course_id}/enrollments"
        params = {
            "type[]": ["StudentEnrollment"],
            "user_id": "self",  # Only get current user's grades
            "include[]": ["grades"],
            "per_page": 100
        }
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            print(f"Grade response for course {course_id}: {response.json()}")  # Debug log
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching grades for course {course_id}: {e}")
            return []

    def get_current_assignments(self, course_id: int) -> List[Dict]:
        """Get current assignments for a specific course"""
        endpoint = f"{self.canvas_url}/api/v1/courses/{course_id}/assignments"
        params = {
            "order_by": "due_at",
            "include[]": ["submission"],
            "bucket": "upcoming",
            "per_page": 100
        }
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching assignments: {e}")
            return []

    def get_all_assignments(self) -> List[Dict]:
        """Get all assignments (cached)"""
        cache_key = 'all_assignments'
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        assignments = []
        try:
            # First get all active courses
            courses = self.get_classes()
            
            # Then get assignments for each course
            for course in courses:
                course_id = course['id']
                endpoint = f"{self.canvas_url}/api/v1/courses/{course_id}/assignments"
                params = {
                    "include[]": ["submission"],
                    "per_page": 100
                }
                
                response = requests.get(endpoint, headers=self.headers, params=params)
                response.raise_for_status()
                course_assignments = response.json()
                
                # Add course information to each assignment
                for assignment in course_assignments:
                    assignment['course_name'] = course.get('name')
                    assignment['course_id'] = course_id
                    assignments.append(assignment)
                    
            result = assignments
            self._set_cached_data(cache_key, result)
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error fetching all assignments: {e}")
            return []

    def get_current_year(self) -> Optional[str]:
        """Get student's current academic year"""
        try:
            user = self.canvas.get_current_user()
            enrollments = user.get_enrollments()
            
            total_credits = 0
            for enrollment in enrollments:
                if hasattr(enrollment, 'grades') and enrollment.grades.get('final_score'):
                    if enrollment.grades['final_score'] >= 60:
                        total_credits += 3
            
            if total_credits < 30:
                return "Freshman"
            elif total_credits < 60:
                return "Sophomore"
            elif total_credits < 90:
                return "Junior"
            else:
                return "Senior"
        except Exception as e:
            print(f"Error determining year: {str(e)}")
            return None

    def get_user_profile_picture(self) -> Optional[str]:
        """Get current user's profile picture URL"""
        endpoint = f"{self.canvas_url}/api/v1/users/self/avatars"
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            avatars = response.json()
            # Return the URL of the first avatar (usually the current one)
            return avatars[0]['url'] if avatars else None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching profile picture: {str(e)}")
            return None