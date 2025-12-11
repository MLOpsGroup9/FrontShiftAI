"""Test authentication endpoints"""
import pytest

def test_health_check(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_success(client, test_db):
    """Test successful login"""
    from db.seed import seed_initial_data
    seed_initial_data(test_db)
    
    response = client.post(
        "/api/auth/login",
        json={"email": "user@crousemedical.com", "password": "password123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "user@crousemedical.com"
    assert data["role"] == "user"
    assert data["company"] == "Crouse Medical Practice"

def test_login_invalid_credentials(client, test_db):
    """Test login with invalid credentials"""
    from db.seed import seed_initial_data
    seed_initial_data(test_db)
    
    response = client.post(
        "/api/auth/login",
        json={"email": "user@crousemedical.com", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_login_nonexistent_user(client, test_db):
    """Test login with non-existent user"""
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"}
    )
    
    assert response.status_code == 401

def test_get_user_info(client, auth_headers):
    """Test getting current user info"""
    response = client.get("/api/auth/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@crousemedical.com"
    assert data["role"] == "user"


def test_get_user_info_invalid_token(client):
    """Test getting user info with invalid token"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401