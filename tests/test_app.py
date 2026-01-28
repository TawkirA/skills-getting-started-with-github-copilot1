"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Test cases for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Soccer Team" in data
        assert "Basketball Club" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Test cases for POST /activities/{activity_name}/signup endpoint"""
    
    def test_successful_signup(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_already_registered(self, client, reset_activities):
        """Test signup when student is already registered"""
        # lucas@mergington.edu is already in Soccer Team
        response = client.post(
            "/activities/Soccer%20Team/signup?email=lucas@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_activity_full(self, client, reset_activities):
        """Test signup when activity is at max capacity"""
        # First, fill up an activity by signing up many students
        # Using an activity with low max_participants
        response = client.get("/activities")
        activities_data = response.json()
        
        # Find an activity with small max_participants
        debate_team = activities_data["Debate Team"]
        current_count = len(debate_team["participants"])
        max_participants = debate_team["max_participants"]
        
        # Sign up students until full
        for i in range(max_participants - current_count):
            email = f"student{i}@mergington.edu"
            response = client.post(
                f"/activities/Debate%20Team/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Try to sign up one more
        response = client.post(
            "/activities/Debate%20Team/signup?email=overfull@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already full" in data["detail"]


class TestUnregisterFromActivity:
    """Test cases for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_successful_unregister(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # lucas@mergington.edu is in Soccer Team
        response = client.delete(
            "/activities/Soccer%20Team/unregister?email=lucas@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "lucas@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistration from activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistration when student is not registered"""
        response = client.delete(
            "/activities/Soccer%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]


class TestSignupAndUnregisterFlow:
    """Test cases for combined signup and unregister operations"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up and then unregistering"""
        email = "testflow@mergington.edu"
        
        # Sign up
        signup_response = client.post(
            f"/activities/Programming%20Class/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Programming Class"]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/Programming%20Class/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Programming Class"]["participants"]
    
    def test_signup_unregister_and_signup_again(self, client, reset_activities):
        """Test signup, unregister, and signup again"""
        email = "testflow2@mergington.edu"
        
        # First signup
        response1 = client.post(
            f"/activities/Art%20Workshop/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(
            f"/activities/Art%20Workshop/unregister?email={email}"
        )
        assert response2.status_code == 200
        
        # Second signup
        response3 = client.post(
            f"/activities/Art%20Workshop/signup?email={email}"
        )
        assert response3.status_code == 200
        
        # Verify registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Art Workshop"]["participants"]
