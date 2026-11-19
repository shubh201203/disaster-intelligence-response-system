import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_citizen_registration():
    email = f"citizen_{uuid.uuid4().hex[:6]}@dirs.org"
    res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Citizen One",
        "role": "CITIZEN"
    })
    assert res.status_code == 201
    assert res.json()["role"] == "CITIZEN"

def test_volunteer_registration():
    email = f"vol_{uuid.uuid4().hex[:6]}@dirs.org"
    res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Vol One",
        "role": "VOLUNTEER"
    })
    assert res.status_code == 201
    assert res.json()["role"] == "VOLUNTEER"

def test_login_invalid_password():
    res = client.post("/api/v1/auth/login", data={
        "username": "nonexistent@dirs.org",
        "password": "WrongPassword"
    })
    assert res.status_code == 401

def test_successful_login_and_token():
    email = f"user_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "User Token Test",
        "role": "CITIZEN"
    })
    res = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_get_current_user_me():
    email = f"user_me_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Pass!", "full_name": "Me Test", "role": "CITIZEN"})
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Pass!"}).json()["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
