# Hostel helpdesk – Hackathon MVP

An MVP of the hostel maintenance application with a select set of features needed for the one-day hackathon demo. Students report issues, admins prioritize them and track the status of the reported incidents.
Features

• Student and admin demo accounts
• Complaint form: category, title, description, etc
• Category-based priority: Low, Medium, High, Critical
• Student track of the complaint status: Submitted → Reviewed → In progress → Resolved
• Card-based UI for an admin to view and edit incidents
• Student emergency contact panel with a prominent “Call” button
• Admin edit panel for emergency phone numbers
• SQLite backend with pre-filled demo data
How to Use
Local Setup

1. Open the project folder in PowerShell
2. Let’s create and initialize the virtual environment:
```ps

py -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install the required packages:
```ps

pip install -r requirements.txt
```

4. Launch the application:
```ps

uvicorn main:app --reload
```

5. Open the link below in your browser: http://127.0.0.1:8000/

Deleting the Seeded Data

Kill the uvicorn server and delete the hostel_helpdesk.db file. It will be replaced with the default set of entries the next time you run the server.

Scope

The authentication system is made as simple as possible due to the MVP scope of the application and its utilization in the hackathon. In the production-grade application, the authentication system would be much more complex with salt and pepper hashing, token-based authorization, rate limiting, and many other security-focused considerations.