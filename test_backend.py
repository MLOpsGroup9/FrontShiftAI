import requests
import json
import sys

BASE_URL = "https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app"

def log(message, status="INFO"):
    print(f"[{status}] {message}")

def test_health():
    log("Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            log("Root endpoint OK", "PASS")
        else:
            log(f"Root endpoint failed: {response.status_code}", "FAIL")
            
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            log("Health endpoint OK", "PASS")
        else:
            log(f"Health endpoint failed: {response.status_code}", "FAIL")
    except Exception as e:
        log(f"Health check exception: {e}", "FAIL")

def test_auth(email, password, role_name):
    log(f"Testing Login for {role_name} ({email})...")
    try:
        payload = {
            "email": email,
            "password": password
        }
        # The backend expects JSON body with email/password, not form data
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                log(f"Login successful for {role_name}", "PASS")
                return token
            else:
                log(f"Login failed for {role_name}: No token returned", "FAIL")
        else:
            log(f"Login failed for {role_name}: {response.status_code} - {response.text}", "FAIL")
    except Exception as e:
        log(f"Login exception for {role_name}: {e}", "FAIL")
    return None

def test_chat(token):
    log("Testing Chat Functionality...")
    if not token:
        log("Skipping chat test due to missing token", "WARN")
        return

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "message": "What is the PTO policy?",
        "history": []
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/chat/message", json=payload, headers=headers)
        if response.status_code == 200:
            answer = response.json().get("response")
            if answer:
                log("Chat response received", "PASS")
                # print(f"Answer: {answer[:100]}...")
            else:
                log("Chat response missing 'response' field", "FAIL")
        else:
            log(f"Chat failed: {response.status_code} - {response.text}", "FAIL")
    except Exception as e:
        log(f"Chat exception: {e}", "FAIL")

def test_admin_companies(token):
    log("Testing Admin Companies List...")
    if not token:
        log("Skipping admin test due to missing token", "WARN")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/admin/companies", headers=headers)
        if response.status_code == 200:
            data = response.json()
            companies = data.get("companies", [])
            if isinstance(companies, list) and len(companies) > 0:
                log(f"Admin companies list retrieved ({len(companies)} companies)", "PASS")
            else:
                log("Admin companies list empty or invalid format", "WARN")
        else:
            log(f"Admin companies list failed: {response.status_code} - {response.text}", "FAIL")
    except Exception as e:
        log(f"Admin companies exception: {e}", "FAIL")

def main():
    log(f"Starting tests against {BASE_URL}")
    
    # 1. Health
    test_health()
    
    # 2. Auth & Functionality
    
    # Super Admin
    admin_token = test_auth("admin@group9.com", "admin123", "Super Admin")
    if admin_token:
        test_admin_companies(admin_token)
        
    # Company Admin
    company_admin_token = test_auth("admin@crousemedical.com", "admin123", "Company Admin")
    
    # Regular User
    user_token = test_auth("user@crousemedical.com", "password123", "Regular User")
    if user_token:
        test_chat(user_token)

if __name__ == "__main__":
    main()
