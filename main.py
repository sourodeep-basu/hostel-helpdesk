from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "hostel_helpdesk.db"
STATUSES = ("Submitted", "Reviewed", "In Progress", "Resolved")
SESSIONS: dict[str, dict] = {}

app = FastAPI(title="Hostel Helpdesk")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@contextmanager
def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def priority_for(category: str, urgency: str, impact: str) -> str:
    """Small, explainable scoring rule suitable for a hackathon MVP."""
    score = {"Low": 1, "Medium": 2, "High": 3}[urgency]
    score += {"Me only": 0, "My room": 1, "Whole floor/block": 2}[impact]
    if category in {"Electrical", "Safety"}:
        score += 1
    if category == "Plumbing" and impact == "Whole floor/block":
        score += 1
    return "Critical" if score >= 5 else "High" if score >= 4 else "Medium" if score >= 2 else "Low"


def row_to_complaint(row: sqlite3.Row) -> dict:
    return dict(row)


def current_user(session_token: str | None = Cookie(default=None)) -> dict:
    user = SESSIONS.get(session_token or "")
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first.")
    return user


class LoginRequest(BaseModel):
    email: str
    password: str


class ComplaintCreate(BaseModel):
    category: str
    title: str = Field(min_length=3, max_length=80)
    description: str = Field(min_length=5, max_length=600)
    location: str = Field(min_length=2, max_length=60)
    urgency: Literal["Low", "Medium", "High"]
    impact: Literal["Me only", "My room", "Whole floor/block"]


class StatusUpdate(BaseModel):
    status: Literal["Submitted", "Reviewed", "In Progress", "Resolved"]


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    phone: str = Field(min_length=3, max_length=30)
    note: str = Field(default="", max_length=80)


@app.on_event("startup")
def initialise_database() -> None:
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin')),
                room TEXT
            );
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                urgency TEXT NOT NULL,
                impact TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            );
            """
        )
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users (name, email, password, role, room) VALUES (?, ?, ?, ?, ?)",
                [
                    ("Aarav Sharma", "student@hostel.demo", "student123", "student", "A-204"),
                    ("Hostel Warden", "admin@hostel.demo", "admin123", "admin", None),
                ],
            )
            student_id = connection.execute("SELECT id FROM users WHERE email = 'student@hostel.demo'").fetchone()[0]
            samples = [
                (student_id, "Aarav Sharma", "Electrical", "Ceiling fan is not working", "The fan has stopped working and the room gets very hot in the afternoon.", "A-204", "High", "My room", "Critical", "In Progress"),
                (student_id, "Aarav Sharma", "Plumbing", "Bathroom tap is leaking", "The washroom tap keeps dripping and water collects on the floor.", "A-204", "Medium", "My room", "Medium", "Reviewed"),
                (student_id, "Aarav Sharma", "Furniture", "Study table drawer is stuck", "The drawer does not open fully.", "A-204", "Low", "Me only", "Low", "Resolved"),
            ]
            connection.executemany(
                """INSERT INTO complaints
                (student_id, student_name, category, title, description, location, urgency, impact, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                samples,
            )
        if connection.execute("SELECT COUNT(*) FROM emergency_contacts").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO emergency_contacts (name, phone, note) VALUES (?, ?, ?)",
                [
                    ("Hostel Warden", "+91 90000 12345", "For urgent hostel support"),
                    ("Campus Security", "+91 90000 67890", "Available day and night"),
                    ("National Emergency", "112", "Police, fire, or medical emergency"),
                ],
            )


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/api/login")
def login(data: LoginRequest, response: Response):
    with db() as connection:
        user = connection.execute(
            "SELECT id, name, email, role, room FROM users WHERE email = ? AND password = ?",
            (data.email.strip().lower(), data.password),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = dict(user)
    response.set_cookie("session_token", token, httponly=True, samesite="lax")
    return dict(user)


@app.post("/api/logout")
def logout(response: Response, session_token: str | None = Cookie(default=None)):
    if session_token:
        SESSIONS.pop(session_token, None)
    response.delete_cookie("session_token")
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return user


@app.get("/api/complaints")
def list_complaints(user: dict = Depends(current_user)):
    with db() as connection:
        if user["role"] == "admin":
            rows = connection.execute("SELECT * FROM complaints ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, created_at DESC").fetchall()
        else:
            rows = connection.execute("SELECT * FROM complaints WHERE student_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return [row_to_complaint(row) for row in rows]


@app.get("/api/contacts")
def list_contacts(user: dict = Depends(current_user)):
    with db() as connection:
        rows = connection.execute("SELECT * FROM emergency_contacts ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/contacts", status_code=201)
def create_contact(data: ContactCreate, user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can add emergency contacts.")
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO emergency_contacts (name, phone, note) VALUES (?, ?, ?)",
            (data.name.strip(), data.phone.strip(), data.note.strip()),
        )
        row = connection.execute("SELECT * FROM emergency_contacts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can remove emergency contacts.")
    with db() as connection:
        cursor = connection.execute("DELETE FROM emergency_contacts WHERE id = ?", (contact_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found.")


@app.post("/api/complaints", status_code=201)
def create_complaint(data: ComplaintCreate, user: dict = Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can submit complaints.")
    priority = priority_for(data.category, data.urgency, data.impact)
    with db() as connection:
        cursor = connection.execute(
            """INSERT INTO complaints (student_id, student_name, category, title, description, location, urgency, impact, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], user["name"], data.category, data.title.strip(), data.description.strip(), data.location.strip(), data.urgency, data.impact, priority),
        )
        row = connection.execute("SELECT * FROM complaints WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_complaint(row)


@app.patch("/api/complaints/{complaint_id}/status")
def update_status(complaint_id: int, data: StatusUpdate, user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can update status.")
    with db() as connection:
        found = connection.execute("SELECT id FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not found:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        connection.execute("UPDATE complaints SET status = ? WHERE id = ?", (data.status, complaint_id))
        row = connection.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    return row_to_complaint(row)
