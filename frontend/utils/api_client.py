import requests
import os
import streamlit as st

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def get_headers():
    """Attach JWT token if available."""
    headers = {}
    if "token" in st.session_state and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return headers

def upload_sheet(file, exam_id: int, set_no: str):
    files = {"file": file}
    data = {"exam_id": exam_id, "set_no": set_no}
    response = requests.post(f"{BASE_URL}/omr/upload/", files=files, data=data, headers=get_headers())
    return response.json()

def get_results(exam_id: int):
    response = requests.get(f"{BASE_URL}/results/{exam_id}", headers=get_headers())
    return response.json()

def export_results(exam_id: int, format: str = "excel"):
    response = requests.get(f"{BASE_URL}/results/{exam_id}/export?format={format}", headers=get_headers())
    return response

def get_flagged(exam_id: int):
    response = requests.get(f"{BASE_URL}/results/{exam_id}/flagged", headers=get_headers())
    return response.json()

def login(username: str, password: str):
    data = {"username": username, "password": password}
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    return response.json()
