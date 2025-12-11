"""Test admin endpoints"""
import pytest

def test_get_company_admins_as_super_admin(client, super_admin_headers):
    """Test getting company admins as super admin"""
    response = client.get("/api/admin/company-admins", headers=super_admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "admins" in data
    assert len(data["admins"]) == 19

def test_get_company_admins_as_regular_user(client, auth_headers):
    """Test that regular users can't access company admins"""
    response = client.get("/api/admin/company-admins", headers=auth_headers)
    
    assert response.status_code == 403

def test_get_company_users_as_admin(client, admin_headers):
    """Test getting company users as company admin"""
    response = client.get("/api/admin/company-users", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "company" in data

def test_add_user_as_admin(client, admin_headers):
    """Test adding a user as company admin"""
    response = client.post(
        "/api/admin/add-user",
        headers=admin_headers,
        json={
            "email": "newuser@crousemedical.com",
            "password": "newpass123",
            "name": "New User"
        }
    )
    
    assert response.status_code == 200
    assert "message" in response.json()

def test_add_duplicate_user(client, admin_headers):
    """Test adding a user that already exists"""
    # Add first time
    client.post(
        "/api/admin/add-user",
        headers=admin_headers,
        json={
            "email": "duplicate@crousemedical.com",
            "password": "pass123",
            "name": "Duplicate User"
        }
    )
    
    # Try to add again
    response = client.post(
        "/api/admin/add-user",
        headers=admin_headers,
        json={
            "email": "duplicate@crousemedical.com",
            "password": "pass123",
            "name": "Duplicate User"
        }
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_delete_user_as_admin(client, admin_headers):
    """Test deleting a user as company admin"""
    # First add a user
    client.post(
        "/api/admin/add-user",
        headers=admin_headers,
        json={
            "email": "todelete@crousemedical.com",
            "password": "pass123",
            "name": "To Delete"
        }
    )
    
    # Then delete - use request() method for DELETE with JSON body
    response = client.request(
        "DELETE",
        "/api/admin/delete-user",
        headers=admin_headers,
        json={"email": "todelete@crousemedical.com"}
    )
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

def test_update_password_as_admin(client, admin_headers):
    """Test updating user password as admin"""
    response = client.put(
        "/api/admin/update-password",
        headers=admin_headers,
        json={
            "email": "user@crousemedical.com",
            "new_password": "newpassword123"
        }
    )
    
    assert response.status_code == 200
    assert "Password updated" in response.json()["message"]