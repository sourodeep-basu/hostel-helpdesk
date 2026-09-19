#Hostel helpdesk – Hackathon MVP

An MVP of the hostel maintenance application with a set of basic features for a one-day hackathon demo. Students can report issues, admins can prioritize them and track the status of the reported incidents.
Features

• Student and admin demo accounts
• Complaint form: category, title, description, etc
• Priority based on category: Low, Medium, High, Critical
• Student track of the complaint status: Submitted → Reviewed → In progress → Resolved
• Card-based UI for an admin to view and edit incidents
• Student emergency contact panel with a prominent “Call” button
• Admin edit panel for emergency phone numbers
• SQLite backend with pre-filled demo data
How to Use
Local Setup

1. Open the project folder in PowerShell
  
2. Let’s create and initialize the virtual environment:
py -m venv .venv
.venv\Scripts\Activate.ps1

3. Install the required packages:
pip install -r requirements.txt

4. Launch the application:
uvicorn main:app --reload

5. Open the link below in your browser:
http://127.0.0.1:8000/

6. Deleting the Seeded Data:
Kill the uvicorn server and delete the hostel_helpdesk.db file. It will be replaced with the default set of entries the next time you run the server.

The authentication system is deliberately kept as simple as possible due to the MVP scope and the application’s intended utilization in a hackathon. In a real-world scenario, the authentication system would require robust security measures such as salt and pepper hashing, token-based authorization, rate limiting, and much more.
