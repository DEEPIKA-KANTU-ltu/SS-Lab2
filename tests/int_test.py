import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from app import app, init_db, DB_PATH_USERS, DB_PATH_ADMINS

# Fixture to set up a temporary test database
@pytest.fixture(scope='module')
def test_db():
    # Create temporary DB files 
    temp_users = tempfile.NamedTemporaryFile(delete=False)
    temp_admins = tempfile.NamedTemporaryFile(delete=False)
    temp_users.close()
    temp_admins.close()
    
    # Override DB paths for testing
    original_users = DB_PATH_USERS
    original_admins = DB_PATH_ADMINS
    app.config['DB_PATH_USERS'] = temp_users.name
    app.config['DB_PATH_ADMINS'] = temp_admins.name
    
    # Initialize test DB
    init_db()
    
    yield temp_users.name, temp_admins.name
    
    # Cleanup
    os.unlink(temp_users.name)
    os.unlink(temp_admins.name)
    app.config['DB_PATH_USERS'] = original_users
    app.config['DB_PATH_ADMINS'] = original_admins

@pytest.fixture
def client(test_db):
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client

# Mock CouchDB to avoid real connections
@pytest.fixture(autouse=True)
def mock_couchdb():
    with patch('app.couch') as mock_couch, \
         patch('app.feedback_db') as mock_feedback_db, \
         patch('app.history_db') as mock_history_db:
        mock_couch.create.return_value = MagicMock()
        mock_feedback_db.save = MagicMock()
        mock_history_db.save = MagicMock()
        mock_history_db.view.return_value = [MagicMock(doc={'user_id': 1, 'timestamp': '2023-01-01'})]
        yield

# Integration Test: Full user journey (register -> login -> add info -> analyze -> feedback)
def test_full_user_journey(client):
    # Register a new user
    response = client.post('/register', data={
        'role': 'user',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'password': 'password123',
        'gender': 'Male',
        'age': '30',
        'work_type': 'Private',
        'residence_type': 'Urban',
        'ever_married': 'Yes'
    })
    assert response.status_code == 302  # Redirect to login
    
    # Login
    response = client.post('/login', data={
        'email': 'john@example.com',
        'password': 'password123',
        'role': 'user'
    })
    assert response.status_code == 302  # Redirect to dashboard
    with client.session_transaction() as sess:
        assert 'user_id' in sess
        assert sess['role'] == 'user'
        user_id = sess['user_id']  # Get actual user ID
    
    # Add medical info
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
    response = client.post('/add_info', data={
        'hypertension': 1,
        'heart_disease': 0,
        'avg_glucose_level': 100.0,
        'bmi': 25.0,
        'smoking_status': 1,
        'stroke': 0
    })
    assert response.status_code == 302  # Redirect to dashboard
    
    # Analyze risk
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
    response = client.get('/analyze')
    assert response.status_code == 200  # Should render analyze page
    # Check for risk category instead of "Risk Score"
    assert b'Low' in response.data or b'Medium' in response.data or b'High' in response.data
    
    # Step 5: Submit feedback
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
    response = client.post('/feedback', data={
        'rating': 5,
        'comment': 'Great app!'
    })
    assert response.status_code == 302  # Redirect to dashboard

# Integration Test: Admin journey (register ->  login -> view user -> delete user)
def test_admin_journey(client):
   # Register admin
    response = client.post('/register', data={
        'role': 'admin',
        'first_name': 'Admin',
        'last_name': 'User',
        'email': 'admin@example.com',
        'password': 'password123',
        'age': '40',
        'gender': 'Female',
        'department': 'IT',
        'contact': '1234567890'
    })
    assert response.status_code == 302
    
    # Login as admin
    response = client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'password123',
        'role': 'admin'
    })
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert 'user_id' in sess
        assert sess['role'] == 'admin'
    
    # Access admin dashboard
    response = client.get('/admin')
    assert response.status_code == 200
    assert b'Total Patients' in response.data  # Check dashboard content
    
    # View users
    response = client.get('/admin/users')
    assert response.status_code == 200
    
    # Delete a user (assuming user ID 1 exists from previous test)
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
    response = client.post('/admin/user/1/delete')
    assert response.status_code == 302

# Integration Test: Error handling (invalid login, duplicate registration)
def test_error_handling(client):
    # Attempt login with wrong password
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'wrong',
        'role': 'user'
    })
    assert response.status_code == 302  # Should redirect with error
    
    # Duplicate registration
    client.post('/register', data={  # First registration
        'role': 'user',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'email': 'jane@example.com',
        'password': 'password123',
        'gender': 'Female',
        'age': '25',
        'work_type': 'Private',
        'residence_type': 'Urban',
        'ever_married': 'No'
    })
    response = client.post('/register', data={  # Duplicate
        'role': 'user',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'email': 'jane@example.com',
        'password': 'password123',
        'gender': 'Female',
        'age': '25',
        'work_type': 'Private',
        'residence_type': 'Urban',
        'ever_married': 'No'
    })
    assert response.status_code == 302  # Should handle duplicate

# Integration Test: Session persistence across requests
def test_session_persistence(client):
    # Register and login
    client.post('/register', data={
        'role': 'user',
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'password123',
        'gender': 'Male',
        'age': '35',
        'work_type': 'Private',
        'residence_type': 'Urban',
        'ever_married': 'Yes'
    })
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123',
        'role': 'user'
    })
    
    # Access dashboard (should be logged in)
    response = client.get('/dashboard')
    assert response.status_code == 200
    
    # Logout
    response = client.get('/logout')
    assert response.status_code == 302
    
    # Try accessing dashboard again (should redirect)
    response = client.get('/dashboard')
    assert response.status_code == 302

# Run tests with pytest
if __name__ == '__main__':
    pytest.main()
