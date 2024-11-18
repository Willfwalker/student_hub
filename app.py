from flask import Flask, jsonify, request, render_template, redirect, url_for, send_file
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from Services.docs_service import DocsService
from Services.canvas_service import CanvasService 
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import calendar
from Services.ai_service import AIService
from Services.inbox_services import InboxService
from PIL import Image

load_dotenv()

app = Flask(__name__, static_folder='static')
app.debug = True
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
csrf = CSRFProtect(app)
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

print("Current working directory:", os.getcwd())
print("Static folder absolute path:", os.path.abspath(app.static_folder))
print("Looking for image at:", os.path.join(app.static_folder, 'images/class-icons/default_icon.png'))
print("Image exists:", os.path.exists(os.path.join(app.static_folder, 'images/class-icons/default_icon.png')))

@app.template_filter('format_date')
def format_date(date_str):
    if not date_str:
        return "No due date"
    try:
        # Parse the ISO format date string
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Format as "month/day"
        return date_obj.strftime("%m/%d")
    except:
        return date_str

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return 'Invalid date'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@cache.cached(timeout=300)
def dashboard():
    canvas_service = CanvasService()
    classes = canvas_service.get_classes()
    user_name = canvas_service.get_user_name()
    user_avatar = canvas_service.get_user_profile_picture()
    
    # Calculate GPA
    total_points = 0
    total_credits = 0
    
    for class_info in classes:
        try:
            grade_info = canvas_service.get_grades(class_info['id'])
            if grade_info and grade_info['percentage'] is not None:
                # Assuming each class is 3 credits
                credits = 3
                percentage = grade_info['percentage']
                
                # Convert percentage to GPA points
                if percentage >= 93: points = 4.0
                elif percentage >= 90: points = 3.7
                elif percentage >= 87: points = 3.3
                elif percentage >= 83: points = 3.0
                elif percentage >= 80: points = 2.7
                elif percentage >= 77: points = 2.3
                elif percentage >= 73: points = 2.0
                elif percentage >= 70: points = 1.7
                elif percentage >= 67: points = 1.3
                elif percentage >= 63: points = 1.0
                elif percentage >= 60: points = 0.7
                else: points = 0.0
                
                total_points += points * credits
                total_credits += credits
                
            class_info['grade'] = f"{grade_info['percentage']:.1f}% ({grade_info['letter']})" if grade_info else 'N/A'
                
        except Exception as e:
            print(f"Error getting grades for {class_info['name']}: {e}")
            class_info['grade'] = 'N/A'
    
    # Calculate final GPA
    calculated_gpa = round(total_points / total_credits, 2) if total_credits > 0 else None
    
    # Get all assignments
    assignments = canvas_service.get_all_assignments()
    
    # Calendar data
    today = datetime.now()
    cal = calendar.monthcalendar(today.year, today.month)
    calendar_days = []
    
    # Get month name and year
    current_month_year = today.strftime('%B %Y')
    
    # Create a dictionary to store assignments by date
    assignment_dict = {}
    for assignment in assignments:
        if assignment.get('due_at'):
            due_date = datetime.strptime(assignment['due_at'], '%Y-%m-%dT%H:%M:%SZ')
            if due_date.year == today.year and due_date.month == today.month:
                date_key = due_date.day
                if date_key not in assignment_dict:
                    assignment_dict[date_key] = []
                assignment_dict[date_key].append({
                    'id': assignment['id'],
                    'course_id': assignment['course_id'],
                    'name': assignment['name'],
                    'course_name': assignment['course_name']
                })
    
    # Calculate previous month's spillover
    if cal[0][0] == 0:
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_days = calendar.monthrange(last_month.year, last_month.month)[1]
        start_day = cal[0].index(1)
        for i in range(start_day):
            calendar_days.append({
                'day': last_month_days - start_day + i + 1,
                'in_month': False,
                'is_today': False,
                'assignments': []
            })
    
    # Current month's days
    for week in cal:
        for day in week:
            if day != 0:
                calendar_days.append({
                    'day': day,
                    'in_month': True,
                    'is_today': day == today.day,
                    'assignments': assignment_dict.get(day, [])
                })
    
    return render_template('dashboard.html', 
                         classes=classes, 
                         user_name=user_name, 
                         user_avatar=user_avatar,
                         calendar_days=calendar_days,
                         current_month_year=current_month_year,
                         calculated_gpa=calculated_gpa)

@app.route('/api/create-homework-doc', methods=['POST'])
def create_homework_doc():
    try:
        docs_service = DocsService()
        canvas_service = CanvasService()
        
        # Get data from request
        data = request.json
        course_id = data.get('course_id')
        assignment_id = data.get('assignment_id')
        check_only = data.get('check_only', False)
        
        if not course_id or not assignment_id:
            return jsonify({'error': 'Missing course_id or assignment_id'}), 400
            
        # Check if document already exists
        existing_doc = docs_service.get_existing_document(str(course_id), str(assignment_id))
        
        # If just checking existence or document exists, return the info
        if check_only or existing_doc:
            return jsonify({'doc_info': existing_doc})
        
        # Get assignment details from Canvas
        assignment_details = canvas_service.get_assignment_details(course_id, assignment_id)
        if not assignment_details:
            return jsonify({'error': 'Assignment not found'}), 404
        
        # Create document using the create_homework_document method
        result = docs_service.create_homework_document(
            canvas_service=canvas_service,
            selected_assignment_index=None,  # Will be determined from the assignment_id
            student_name=None,  # Will be fetched from Canvas
            professor=None  # Will be fetched from Canvas
        )
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 500
            
        if result.get('doc_info'):
            return jsonify({'status': 'document_created', 'doc_info': result['doc_info']})
        
        return jsonify({'error': 'Failed to create document'}), 500

    except Exception as e:
        print(f"Error in create_homework_doc: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/assignments')
@cache.cached(timeout=300)
def assignments():
    canvas_service = CanvasService()
    courses = canvas_service.get_classes()
    
    # Get assignments for each course
    assignments = {}
    for course in courses:
        course_assignments = canvas_service.get_current_assignments(course['id'])
        if course_assignments:
            # Process each assignment to ensure it has html_url
            processed_assignments = []
            for assignment in course_assignments:
                processed_assignment = assignment.copy()  # Create a copy of the assignment
                # Construct the Canvas URL for the assignment if it's not already present
                if 'html_url' not in processed_assignment:
                    processed_assignment['html_url'] = f"{canvas_service.canvas_url}/courses/{course['id']}/assignments/{assignment['id']}"
                processed_assignments.append(processed_assignment)
            assignments[course['id']] = processed_assignments
    
    return render_template('assignments.html', 
                         courses=courses,
                         assignments=assignments)

@app.route('/make-hw-doc')
def make_hw_doc():
    canvas_service = CanvasService()
    courses = canvas_service.get_classes()
    
    # Get assignments for each course
    assignments = []
    for course in courses:
        course_assignments = canvas_service.get_current_assignments(course['id'])
        for assignment in course_assignments:
            assignments.append({
                'index': len(assignments),
                'name': assignment['name'],
                'course_name': course['name'],
                'due_date': format_date(assignment.get('due_at', 'No due date')),
                'course_id': course['id'],
                'assignment_id': assignment['id']
            })
    
    return render_template('make_hw_doc.html', assignments=assignments)

@app.route('/summarize-text', methods=['GET'])
@app.route('/summarize-text/', methods=['GET'])
def summarize_text():
    return render_template('summarize_text.html')

@app.route('/api/summarize-text', methods=['POST'])
@csrf.exempt
def api_summarize_text():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        ai_service = AIService()
        try:
            summary = ai_service.summarize_text(text)
            if summary:
                return jsonify({'summary': summary})
            else:
                return jsonify({'error': 'Failed to generate summary - empty response'}), 500
        except Exception as e:
            print(f"AI Service error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/recommend-videos', methods=['POST'])
@csrf.exempt
def api_recommend_videos():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        ai_service = AIService()
        try:
            video_urls = ai_service.recommend_videos(prompt)
            if video_urls:
                return jsonify({'videos': video_urls})
            else:
                return jsonify({'error': 'Failed to get video recommendations'}), 500
        except Exception as e:
            print(f"AI Service error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/recommend-videos')
def recommend_videos():
    prompt = request.args.get('prompt', '')
    if not prompt:
        return redirect(url_for('dashboard'))
    
    ai_service = AIService()
    try:
        print(f"Searching for videos with prompt: {prompt}")  # Debug log
        videos = ai_service.recommend_videos(prompt)
        print(f"Received videos: {videos}")  # Debug log
        if not videos:
            print("No videos returned")  # Debug log
            videos = []
    except Exception as e:
        print(f"Error getting video recommendations: {e}")
        videos = []
    
    return render_template('recommend_videos.html', videos=videos, prompt=prompt)

@app.route('/video-prompt')
def video_prompt():
    return render_template('video_prompt.html')

@app.route('/check-grades')
@cache.cached(timeout=300)
def check_grades():
    try:
        canvas_service = CanvasService()
        courses = canvas_service.get_classes()
        
        # Get grades for each course
        courses_with_grades = []
        for course in courses:
            print(f"\nProcessing course: {course['name']}")  # Debug log
            grades = canvas_service.get_grades(course['id'])
            print(f"Raw grades data: {grades}")  # Debug log
            
            if grades:
                for enrollment in grades:
                    # Check if this enrollment belongs to the current user
                    if enrollment.get('type') == 'StudentEnrollment':
                        # Get the grade from the grades object
                        grade_data = enrollment.get('grades', {})
                        print(f"Grade data: {grade_data}")  # Debug log
                        
                        # Try to get any available score in this order:
                        # 1. Current score
                        # 2. Final score
                        # 3. Unposted current score
                        grade = grade_data.get('current_score')
                        if grade is None:
                            grade = grade_data.get('final_score')
                        if grade is None:
                            grade = grade_data.get('unposted_current_score')
                        
                        courses_with_grades.append({
                            'name': course['name'],
                            'grade': grade if grade is not None else 'N/A'
                        })
                        print(f"Added course with grade: {grade}")  # Debug log
                        break  # Found the student enrollment, no need to check others
    
        print(f"Final courses_with_grades: {courses_with_grades}")  # Debug log
        return render_template('check_grades.html', courses=courses_with_grades)
        
    except Exception as e:
        print(f"Error in check_grades: {str(e)}")  # Debug log
        return render_template('check_grades.html', courses=[], error=str(e))

@app.route('/create-lecture-summary')
def create_lecture_summary():
    return render_template('create_lecture_summary.html')

@app.route('/api/create-lecture-summary', methods=['POST'])
@csrf.exempt
def api_create_lecture_summary():
    try:
        duration = request.json.get('duration')
        if not duration:
            return jsonify({'error': 'No duration provided'}), 400

        ai_service = AIService()
        try:
            summary = ai_service.create_lecture_summary(duration)
            if summary:
                return jsonify({'summary': summary})
            else:
                return jsonify({'error': 'Failed to create summary - empty response'}), 500
        except Exception as e:
            print(f"AI Service error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/lecture-summary-result')
def lecture_summary_result():
    summary = request.args.get('summary', '')
    return render_template('lecture_summary_result.html', summary=summary)

@app.route('/get-hw-help', methods=['GET'])
def get_hw_help():
    print("Rendering homework help page")
    return render_template('get_hw_help.html')

@app.route('/api/get-hw-help', methods=['POST'])
@csrf.exempt
def api_get_hw_help():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        ai_service = AIService()
        response = ai_service.get_ai_response(prompt)
        if response:
            return jsonify({'response': response})
        else:
            return jsonify({'error': 'Failed to get AI response'}), 500
            
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/check-inbox')
@cache.cached(timeout=300)
def check_inbox():
    try:
        inbox_service = InboxService()
        sender = request.args.get('sender', 'all') 
        
        try:
            allowed_senders = inbox_service.allowed_senders
            print(f"Loaded allowed senders: {allowed_senders}")  # Debug print

        except Exception as e:
            print(f"Error getting allowed senders: {str(e)}")  # Debug print
            allowed_senders = []
        
        emails = []
        if sender:
            try:
                response = inbox_service.get_emails_from_sender(sender)
                # Check if response is a dictionary and get emails from it
                if isinstance(response, dict):
                    emails = response.get('emails', [])
                else:
                    # If response is a list, use it directly
                    emails = response if isinstance(response, list) else []
                
            except Exception as e:
                print(f"Error getting emails: {str(e)}")  
                return render_template('check_inbox.html', 
                                    emails=[],
                                    allowed_senders=allowed_senders,
                                    error=str(e))
                                    
        return render_template('check_inbox.html', 
                             emails=emails,
                             allowed_senders=allowed_senders,
                             current_sender=sender)
    except Exception as e:
        print(f"Error in check_inbox route: {str(e)}") 
        return render_template('check_inbox.html', 
                             emails=[],
                             allowed_senders=[],
                             error=str(e))

@app.route('/todo-list')
def todo_list():
    return render_template('to-do_list_creator.html')

@app.route('/api/generate-todo-pdf', methods=['POST'])
@csrf.exempt
def generate_todo_pdf():
    try:
        data = request.json
        title = data.get('title', 'Todo List')
        items = data.get('items', [])
        
        canvas_service = CanvasService()
        pdf_path = canvas_service.create_todo_list(title, items)
        
        if pdf_path and os.path.exists(pdf_path):
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='todo_list.pdf'
            )
        else:
            return jsonify({'error': 'Failed to generate PDF'}), 500
            
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/get-assignments')
def get_assignments_api():
    try:
        canvas_service = CanvasService()
        assignments = canvas_service.get_all_assignments()
        return jsonify(assignments)
    except Exception as e:
        print(f"Error fetching assignments: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/assignment-details/<int:course_id>/<int:assignment_id>')
def get_assignment_details(course_id, assignment_id):
    try:
        canvas_service = CanvasService()
        assignments = canvas_service.get_current_assignments(course_id)
        
        # Find the specific assignment
        assignment = next((a for a in assignments if a['id'] == assignment_id), None)
        
        if assignment:
            # Get the course name
            courses = canvas_service.get_classes()
            course = next((c for c in courses if c['id'] == course_id), None)
            if course:
                assignment['course_name'] = course['name']
            
            return jsonify(assignment)
        else:
            return jsonify({'error': 'Assignment not found'}), 404
            
    except Exception as e:
        print(f"Error getting assignment details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/course/<int:course_id>')
def course_page(course_id):
    try:
        canvas_service = CanvasService()
        course = next((c for c in canvas_service.get_classes() if c['id'] == course_id), None)
        
        if not course:
            return "Course not found", 404

        # Get the grade info if it's not already in the course object
        if 'grade' not in course:
            grade_info = canvas_service.get_grades(course_id)
            if grade_info and grade_info['percentage'] is not None:
                course['grade'] = f"{grade_info['percentage']:.1f}% ({grade_info['letter']})"
            else:
                course['grade'] = 'N/A'

        # Get current assignments
        assignments = canvas_service.get_current_assignments(course_id)
        
        # Get past assignments
        past_assignments = canvas_service.get_past_assignments(course_id)
        
        # Process assignments to ensure they have html_url
        processed_assignments = []
        for assignment in assignments:
            processed_assignment = assignment.copy()
            if 'html_url' not in processed_assignment:
                processed_assignment['html_url'] = f"{canvas_service.canvas_url}/courses/{course_id}/assignments/{assignment['id']}"
            processed_assignments.append(processed_assignment)
        
        return render_template('course_page.html', 
                             course=course,
                             assignments=processed_assignments,
                             past_assignments=past_assignments)
    except Exception as e:
        print(f"Error in course_page: {str(e)}")
        return str(e), 500

@app.route('/select-assignment-for-videos')
def select_assignment_for_videos():
    try:
        canvas_service = CanvasService()
        courses = canvas_service.get_classes()
        
        current_time = datetime.now()
        two_weeks_future = current_time + timedelta(days=14)
        
        current_assignments = []
        for course in courses:
            try:
                course_assignments = canvas_service.get_current_assignments(course['id'])
                if course_assignments:
                    for assignment in course_assignments:
                        if assignment.get('due_at'):
                            due_date = datetime.strptime(assignment['due_at'], '%Y-%m-%dT%H:%M:%SZ')
                            if (due_date > current_time - timedelta(days=1) and 
                                due_date < two_weeks_future):
                                # Add course name to assignment
                                assignment['course_name'] = course['name']
                                # Ensure description exists and is a string
                                assignment['description'] = str(assignment.get('description', ''))
                                # Clean description HTML if present
                                if assignment['description']:
                                    # Basic HTML tag removal (you might want to use a proper HTML parser)
                                    description = assignment['description'].replace('<p>', '').replace('</p>', '\n')
                                    assignment['description'] = description.strip()
                                current_assignments.append(assignment)
            except Exception as e:
                print(f"Error processing course {course['name']}: {e}")
                continue
        
        # Sort by due date
        current_assignments.sort(key=lambda x: datetime.strptime(x['due_at'], '%Y-%m-%dT%H:%M:%SZ'))
        
        return render_template('select_assignment_for_videos.html', 
                             assignments=current_assignments)
                             
    except Exception as e:
        print(f"Error in select_assignment_for_videos: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/api/get-video-prompt', methods=['POST'])
@csrf.exempt
def api_get_video_prompt():
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')

        print(f"Received request - Name: {name}, Description: {description}")  # Debug log
        
        if not name:
            return jsonify({'error': 'Assignment name is required'}), 400
            
        # Use a default description if none provided
        description = description or "No description available"
        
        ai_service = AIService()
        search_prompt = ai_service.create_video_search_prompt(name, description)
        
        if search_prompt:
            print(f"Generated prompt: {search_prompt}")  # Debug log
            return jsonify({'prompt': search_prompt})
        else:
            return jsonify({'error': 'Failed to generate search prompt'}), 500
            
    except Exception as e:
        print(f"Error in api_get_video_prompt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/graphing-calculator')
def graphing_calculator():
    return render_template('desmos.html')

@app.route('/assignment/<int:course_id>/<int:assignment_id>')
@cache.cached(timeout=300)
def assignment_details(course_id, assignment_id):
    try:
        canvas_service = CanvasService()
        details = canvas_service.get_assignment_details(course_id, assignment_id)
        
        if not details:
            return "Assignment not found", 404
            
        # Add submission types if not present
        if 'submission_types' not in details:
            details['submission_types'] = []
            
        # Ensure all required fields are present
        required_fields = ['title', 'professor', 'description', 'due_date', 
                         'points_possible', 'submission_types', 'course_id']
        for field in required_fields:
            if field not in details:
                details[field] = 'N/A'
                
        return render_template('assignment_details.html', assignment=details)
    except Exception as e:
        print(f"Error in assignment_details: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    app.debug = True  # Enable debug mode
    app.run(debug=True)  # Enable auto-reloader