from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
import datetime
import csv
from typing import Optional, Dict, List
import pandas as pd
from datetime import datetime
from os import getenv
from dotenv import load_dotenv

class DocsService:
    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self):
        load_dotenv()
        
        # Get absolute paths from environment variables
        base_path = "/Users/willwalker/Desktop/Website/student_hub_functions"
        self.credentials_path = os.path.join(base_path, 'credentials.json')
        self.folder_ids_path = os.path.join(base_path, 'Folder_Ids.csv')
        
        if not os.path.exists(self.credentials_path):
            raise ValueError(f"Credentials file not found at: {self.credentials_path}")
        
        if not os.path.exists(self.folder_ids_path):
            raise ValueError(f"Folder IDs file not found at: {self.folder_ids_path}")
        
        self.folder_ids_df = pd.read_csv(self.folder_ids_path)
        self.credentials = self._get_credentials()
        self.docs_service = build('docs', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    def _get_credentials(self) -> Credentials:
        """Gets and refreshes Google API credentials."""
        creds = None
        token_path = os.path.join(os.path.dirname(self.credentials_path), 'token.pickle')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

    def create_document(self, title: str) -> Optional[Dict]:
        """Creates a new Google Doc with the given title."""
        try:
            document = self.docs_service.documents().create(
                body={'title': title}).execute()
            print(f'Created document with title: {title}')
            return document
        except Exception as e:
            print(f'Error creating document: {e}')
            return None

    def update_document(self, document_id: str, name: str, professor: str, class_name: str) -> Optional[Dict]:
        try:
            # Create header
            header_requests = [{'createHeader': {'type': 'DEFAULT'}}]
            self.docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': header_requests}
            ).execute()

            # Get header ID
            doc = self.docs_service.documents().get(
                documentId=document_id).execute()
            header_id = doc.get('headers', {}).popitem()[0]

            # Get current date
            current_date = datetime.now().strftime('%d %B %Y')
            last_name = name.split()[-1]

            # Update header and content with proper formatting
            requests = [
                # Header content (Last Name #) - Right aligned
                {
                    'insertText': {
                        'location': {'segmentId': header_id, 'index': 0},
                        'text': f"{last_name} 1"
                    }
                },
                # Right align the header text
                {
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': 0,
                            'endIndex': len(last_name) + 2,
                            'segmentId': header_id
                        },
                        'paragraphStyle': {
                            'alignment': 'END'  # This aligns text to the right
                        },
                        'fields': 'alignment'
                    }
                },
                # Main content with proper spacing and order
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': f"{name}\n{professor}\n{class_name}\n{current_date}\n\n"
                    }
                },
                # Apply Times New Roman font to entire document
                {
                    'updateTextStyle': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': len(name) + len(professor) + len(class_name) + len(current_date) + 5
                        },
                        'textStyle': {
                            'fontSize': {'magnitude': 12, 'unit': 'PT'},
                            'weightedFontFamily': {'fontFamily': 'Times New Roman'}
                        },
                        'fields': 'fontSize,weightedFontFamily'
                    }
                },
                # Make text double-spaced
                {
                    'updateParagraphStyle': {
                        'range': {'startIndex': 1, 'endIndex': len(name) + len(professor) + len(class_name) + len(current_date) + 5},
                        'paragraphStyle': {
                            'lineSpacing': 200,
                            'alignment': 'START'
                        },
                        'fields': 'lineSpacing,alignment'
                    }
                }
            ]

            result = self.docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()

            return result
        except Exception as e:
            print(f'Error updating document: {e}')
            return None

    def move_to_folder(self, file_id: str, folder_id: str) -> bool:
        """Moves a file to specified folder in Google Drive."""
        try:
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return True
        except Exception as e:
            print(f'Error moving file: {e}')
            return False

    def create_class_folders(self, parent_folder_id: str, class_names: list) -> list:
        """Creates folders for each class."""
        created_folders = []
        for class_name in class_names:
            try:
                folder_metadata = {
                    'name': class_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_folder_id]
                }
                
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                folder_id = folder.get('id')
                self._save_folder_info(class_name, folder_id)
                created_folders.append(folder_id)
                
            except Exception as e:
                print(f'Error creating folder for {class_name}: {e}')
                
        return created_folders

    def _save_folder_info(self, folder_name: str, folder_id: str):
        """Saves folder information to CSV."""
        existing_entries = set()
        if os.path.isfile(self.folder_ids_path):
            with open(self.folder_ids_path, 'r', newline='') as file:
                reader = csv.reader(file)
                next(reader, None)
                existing_entries = {row[1] for row in reader}
        
        if folder_name not in existing_entries:
            file_exists = os.path.isfile(self.folder_ids_path)
            with open(self.folder_ids_path, 'a', newline='') as file:
                writer = csv.writer(file, quoting=csv.QUOTE_NONNUMERIC)
                if not file_exists:
                    writer.writerow(['Folder Name', 'Folder ID'])
                writer.writerow([folder_name, folder_id])

    def create_homework_document(self, canvas_service, selected_assignment_index=None, student_name=None, professor=None) -> Dict:
        try:
            # Get student name from Canvas if not provided
            if student_name is None:
                student_name = canvas_service.get_user_name()
                if not student_name:
                    return {"error": "Could not get student name from Canvas"}

            # Get all assignments from Canvas
            assignments = []
            courses = canvas_service.get_classes()
            
            # Collect assignments in a list
            for course in courses:
                course_assignments = canvas_service.get_current_assignments(course['id'])
                professor = canvas_service.get_course_professor(course['id'])  # Get professor for each course
                
                for assignment in course_assignments:
                    due_date = assignment.get("due_at")
                    if due_date:
                        due_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M:%SZ")
                        due_date = due_date.strftime("%B %d, %Y at %I:%M %p")
                    
                    assignment_info = {
                        'index': len(assignments),
                        'course_name': course['name'],
                        'name': assignment.get('name'),
                        'due_date': due_date or 'No due date',
                        'course_id': course['id'],
                        'assignment_data': assignment
                    }
                    assignments.append(assignment_info)

            # If no assignment is selected, return the list of assignments
            if selected_assignment_index is None:
                return {
                    "assignments": assignments,
                    "status": "pending_selection"
                }

            # If an assignment is selected, create the document
            selected_assignment = assignments[selected_assignment_index]
            
            # Get folder ID for the class
            folder_id = self._get_folder_id(selected_assignment['course_name'])
            if not folder_id:
                return {"error": "Could not find folder ID for class"}

            # Create and setup document
            doc_info = self._create_and_setup_document(
                assignment=selected_assignment,
                student_name=student_name,
                professor=professor,
                folder_id=folder_id
            )

            if doc_info:
                return {
                    "status": "document_created",
                    "doc_info": doc_info
                }
            else:
                return {"error": "Failed to create document"}

        except Exception as e:
            return {"error": f"Error in create_homework_document: {str(e)}"}

    def _get_assignment_selection(self, assignments: List[Dict]) -> Optional[Dict]:
        """Get user selection for assignment"""
        while True:
            try:
                selection = int(input("\nEnter the number of the assignment you want to work on: "))
                if 0 <= selection < len(assignments):
                    selected = assignments[selection]
                    print(f"\nYou selected: {selected['name']} from {selected['course_name']}")
                    return selected
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
            except Exception as e:
                print(f"Error in assignment selection: {e}")
                return None

    def _get_folder_id(self, class_name: str) -> Optional[str]:
        """Get folder ID from CSV for given class"""
        try:
            folder_id = self.folder_ids_df.loc[
                self.folder_ids_df['Folder Name'] == class_name, 
                'Folder ID'
            ].iloc[0]
            return folder_id
        except (FileNotFoundError, IndexError) as e:
            print(f"Error: Could not find folder ID for {class_name}: {e}")
            return None

    def _create_and_setup_document(self, 
                                 assignment: Dict,
                                 student_name: str,
                                 professor: str,
                                 folder_id: str) -> Optional[Dict]:
        """Create and setup the document with initial content"""
        try:
            # Create document
            doc = self.create_document(assignment['name'])
            if not doc:
                return None

            document_id = doc.get('documentId')
            
            # Update document content
            self.update_document(
                document_id=document_id,
                name=student_name,
                professor=professor,
                class_name=assignment['course_name']
            )

            # Move to appropriate folder
            self.move_to_folder(document_id, folder_id)

            # Create return info
            doc_info = {
                'document_id': document_id,
                'assignment_name': assignment['name'],
                'course_name': assignment['course_name'],
                'url': f'https://docs.google.com/document/d/{document_id}/edit'
            }

            print("\nDocument created and set up successfully!")
            print(f"You can view your document at: {doc_info['url']}")

            return doc_info

        except Exception as e:
            print(f"Error setting up document: {e}")
            return None