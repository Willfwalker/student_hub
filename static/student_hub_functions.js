document.addEventListener('DOMContentLoaded', function() {
    // Add your existing code here
    
    // Add event listeners for the buttons
    document.getElementById('check-inbox')?.addEventListener('click', function() {
        window.location.href = '/check-inbox';
    });

    document.getElementById('check-grades')?.addEventListener('click', function() {
        window.location.href = '/check-grades';
    });

    document.getElementById('recommend-videos')?.addEventListener('click', function() {
        const modal = document.getElementById('videoRecommendModal');
        modal.style.display = 'block';

        // Close modal when clicking X
        modal.querySelector('.close-modal').addEventListener('click', function() {
            modal.style.display = 'none';
        });

        // Close modal when clicking outside
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });

        // Handle user prompt option
        document.getElementById('user-prompt-option').addEventListener('click', function() {
            window.location.href = '/video-prompt';
            document.getElementById('videoRecommendModal').style.display = 'none';
        });

        // Handle assignments option
        document.getElementById('assignments-option').addEventListener('click', function() {
            // Temporarily using alert, you can replace with actual implementation
            alert('Assignments option selected - Implementation coming soon');
            modal.style.display = 'none';
        });
    });

    document.getElementById('lecture-summary')?.addEventListener('click', function() {
        window.location.href = '/create-lecture-summary';
    });

    document.getElementById('homework-help')?.addEventListener('click', function() {
        console.log('Homework help button clicked');
        window.location.href = '/get-hw-help';
    });

    // Add event listener for summarize text
    document.getElementById('summarize-text')?.addEventListener('click', function() {
        window.location.href = '/summarize-text';
    });

    // Add event listener for sender selection changes
    document.getElementById('senderSelect')?.addEventListener('change', function() {
        const sender = this.value;
        window.location.href = `/check-inbox?sender=${encodeURIComponent(sender)}`;
    });

    // Add auto-refresh functionality for inbox (every 5 minutes)
    if (window.location.pathname === '/check-inbox') {
        setInterval(function() {
            const currentSender = document.getElementById('senderSelect')?.value;
            if (currentSender) {
                window.location.href = `/check-inbox?sender=${encodeURIComponent(currentSender)}`;
            }
        }, 300000); // 5 minutes in milliseconds
    }

    // Add calendar functionality
    const calendar = document.querySelector('.calendar');
    if (calendar) {
        // Add hover effect for assignment cells
        const assignmentCells = document.querySelectorAll('.day .assignment');
        assignmentCells.forEach(cell => {
            cell.addEventListener('mouseenter', function() {
                this.style.background = 'rgba(65, 105, 225, 0.5)';  // Lighter blue on hover
            });
            
            cell.addEventListener('mouseleave', function() {
                this.style.background = 'rgba(65, 105, 225, 0.3)';  // Back to original color
            });
        });

        // Make assignments clickable
        const assignments = document.querySelectorAll('.assignment');
        assignments.forEach(assignment => {
            assignment.style.cursor = 'pointer';
            assignment.addEventListener('click', function() {
                // You can add functionality here to show more details about the assignment
                // For now, just show the full name in case it was truncated
                alert(this.textContent);
            });
        });
    }

    // Add calendar navigation (if needed later)
    function updateCalendar(year, month) {
        // This function can be implemented later if you want to add
        // month navigation functionality
        fetch(`/api/calendar?year=${year}&month=${month}`)
            .then(response => response.json())
            .then(data => {
                // Update calendar with new data
            });
    }

    // Add this with your other event listeners
    document.getElementById('todo-list')?.addEventListener('click', function() {
        window.location.href = '/todo-list';
    });

    // Add lazy loading for assignments
    function loadAssignments() {
        const assignmentsContainer = document.querySelector('.assignments-container');
        if (!assignmentsContainer) return;

        fetch('/api/get-assignments')
            .then(response => response.json())
            .then(assignments => {
                // Render assignments
                assignmentsContainer.innerHTML = assignments.map(assignment => `
                    <div class="assignment-card">
                        <h3>${assignment.name}</h3>
                        <p>${assignment.course_name}</p>
                        <p>Due: ${assignment.due_date}</p>
                    </div>
                `).join('');
            });
    }

    // Lazy load assignments if we're on the assignments page
    if (window.location.pathname === '/assignments') {
        loadAssignments();
    }
});

async function createHomeworkDoc() {
    try {
        window.location.href = '/assignments';
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
}

function showAssignmentSelectionDialog(assignments) {
    return new Promise((resolve) => {
        const dialog = document.createElement('div');
        dialog.className = 'assignment-dialog';
        
        const content = document.createElement('div');
        content.innerHTML = `
            <h3>Select an Assignment</h3>
            ${assignments.map((assignment, index) => `
                <div class="assignment-item" data-index="${index}">
                    <h4>${assignment.name}</h4>
                    <p>Course: ${assignment.course_name}</p>
                    <p>Due: ${assignment.due_date}</p>
                </div>
            `).join('')}
        `;

        dialog.appendChild(content);
        document.body.appendChild(dialog);

        // Add click handlers
        const items = dialog.querySelectorAll('.assignment-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                dialog.remove();
                resolve(index);
            });
        });
    });
}

function promptForInput(message) {
    return new Promise((resolve) => {
        const input = prompt(message);
        resolve(input);
    });
}