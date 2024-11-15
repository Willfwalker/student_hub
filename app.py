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

load_dotenv()

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
csrf = CSRFProtect(app)
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})
@app.template_filter('format_date')
def format_date(date_str):
    if not date_str or date_str == 'No due date':
        return 'No due date'
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        return date_obj.strftime('%B %d, %Y at %I:%M %p')
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
                         current_month_year=current_month_year)

@app.route('/api/create-homework-doc', methods=['POST'])
def create_homework_doc():
    try:
        docs_service = DocsService()
        canvas_service = CanvasService()
        
        # Convert the index to integer
        selected_index = request.json.get('selected_assignment_index')
        if selected_index is not None:
            selected_index = int(selected_index)
        
        result = docs_service.create_homework_document(
            canvas_service=canvas_service,
            selected_assignment_index=selected_index,
            student_name=request.json.get('student_name'),
            professor=request.json.get('professor')
        )
        
        return jsonify(result)
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

if __name__ == '__main__':
    app.debug = True  # Enable debug mode
    app.run(debug=True)  # Enable auto-reloader