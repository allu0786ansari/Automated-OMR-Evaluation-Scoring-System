import requests
import os

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def upload_sheet(file, exam_id: int, set_no: str):
    """Upload OMR sheet for processing."""
    files = {"file": file}
    data = {"exam_id": exam_id, "set_no": set_no}
    response = requests.post(f"{BASE_URL}/omr/upload/", files=files, data=data)
    return response.json()

def get_results(exam_id: int):
    """Fetch results for an exam."""
    response = requests.get(f"{BASE_URL}/results/{exam_id}")
    return response.json()

def export_results(exam_id: int, format: str = "excel"):
    """Export results in CSV/Excel format."""
    response = requests.get(f"{BASE_URL}/results/{exam_id}/export?format={format}")
    return response

def get_flagged(exam_id: int):
    """Fetch flagged/ambiguous sheets for review."""
    response = requests.get(f"{BASE_URL}/results/{exam_id}/flagged")
    return response.json()

def login(username: str, password: str):
    """Simple login to get token (if auth is enabled)."""
    data = {"username": username, "password": password}
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    return response.json()
