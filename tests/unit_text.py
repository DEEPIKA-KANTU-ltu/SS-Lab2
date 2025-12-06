import pytest
from unittest.mock import patch, MagicMock
import sqlite3
import os
import tempfile
from app import app, init_db, compute_risk, DB_PATH_USERS, DB_PATH_ADMINS  # Ensure your app file is named app.py

# Fixture for Flask test client
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client

# Fixture to mock databases
@pytest.fixture
def mock_db():
    with patch('app.sqlite3.connect') as mock_connect:  # Updated patch target
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        yield mock_conn, mock_cursor

# Expanded Test compute_risk function with more edge cases
def test_compute_risk():
    # Test case 1: Low risk
    user_row = {
        "age": 25,
        "bmi": 22.0,
        "avg_glucose_level": 90.0,
        "hypertension": 0,
        "heart_disease": 0
    }
    assert compute_risk(user_row) == 0.0

    # Test case 2: High risk (corrected expectation)
    user_row = {
        "age": 65,
        "bmi": 35.0,
        "avg_glucose_level": 140.0,
        "hypertension": 1,
        "heart_disease": 1
    }
    expected = 0.25 + 0.15 + 0.2 + 0.2 + 0.15  # 0.95
    assert compute_risk(user_row) == 0.95

    # Test case 3: Medium risk
    user_row = {
        "age": 50,
        "bmi": 28.0,
        "avg_glucose_level": 110.0,
        "hypertension": 0,
        "heart_disease": 1
    }
    expected = 0.15 + 0.08 + 0.2 + 0.08  # 0.51
    assert compute_risk(user_row) == 0.51

    # New edge case: Boundary age (exactly 60)
    user_row = {
        "age": 60,
        "bmi": 30.0,
        "avg_glucose_level": 126.0,
        "hypertension": 1,
        "heart_disease": 0
    }
    expected = 0.25 + 0.15 + 0.2 + 0.15  # 0.75
    assert compute_risk(user_row) == 0.75

    # New edge case: High risk but not max (0.95, not 1.0)
    user_row = {
        "age": 70,
        "bmi": 40.0,
        "avg_glucose_level": 200.0,
        "hypertension": 1,
        "heart_disease": 1
    }
    # 0.25 (age) + 0.15 (bmi) + 0.2 (hypertension) + 0.2 (heart) + 0.15 (glucose) = 0.95
    assert compute_risk(user_row) == 0.95  # Corrected: not capped to 1.0

    # New edge case: Invalid/None values (should handle gracefully)
    user_row = {
        "age": None,
        "bmi": None,
        "avg_glucose_level": None,
        "hypertension": None,
        "heart_disease": None
    }
    assert compute_risk(user_row) == 0.0  

    # New edge case: Negative values (should still compute)
    user_row = {
        "age": -10,
        "bmi": -5.0,
        "avg_glucose_level": -50.0,
        "hypertension": 0,
        "heart_disease": 0
    }
    assert compute_risk(user_row) == 0.0  # No positive scores

# Test init_db function (unchanged)
@patch('app.sqlite3.connect')
def test_init_db(mock_connect):
    mock_conn_users = MagicMock()
    mock_conn_admins = MagicMock()
    mock_cursor_users = MagicMock()
    mock_cursor_admins = MagicMock()
    mock_conn_users.cursor.return_value = mock_cursor_users
    mock_conn_admins.cursor.return_value = mock_cursor_admins
    
    mock_connect.side_effect = [mock_conn_users, mock_conn_admins]
    
    init_db()
    
    assert mock_cursor_users.execute.call_count >= 3
    mock_conn_users.commit.assert_called()
    mock_conn_users.close.assert_called()
    
    assert mock_cursor_admins.execute.call_count == 1
    mock_conn_admins.commit.assert_called()
    mock_conn_admins.close.assert_called()

# Expanded Test registration route for user with edge cases
@patch('app.sqlite3.connect')
def test_register_user(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock no existing user
    mock_cursor.fetchone.return_value = None
    
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
    
    assert response.status_code == 302
    mock_cursor.execute.assert_called()
    mock_conn.commit.assert_called()

    # New edge case: Duplicate email
    mock_cursor.fetchone.return_value = (1,)  # Simulate existing user
    response = client.post('/register', data={
        'role': 'user',
        'first_name': 'Jane',
        'last_name': 'Doe',
        'email': 'john@example.com',  # Duplicate
        'password': 'password123',
        'gender': 'Female',
        'age': '25',
        'work_type': 'Self-employed',
        'residence_type': 'Rural',
        'ever_married': 'No'
    })
    assert response.status_code == 302  # Should redirect with flash

    # New edge case: Missing required fields
    response = client.post('/register', data={
        'role': 'user',
        'first_name': '',
        'last_name': '',
        'email': '',
        'password': '',
        'gender': '',
        'age': '',
        'work_type': '',
        'residence_type': '',
        'ever_married': ''
    })
    assert response.status_code == 302  # Should handle gracefully

# Expanded Test registration route for admin with edge cases
@patch('app.sqlite3.connect')
def test_register_admin(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock no existing admin
    mock_cursor.fetchone.return_value = None
    
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
    mock_cursor.execute.assert_called()
    mock_conn.commit.assert_called()

    # New edge case: Duplicate email
    mock_cursor.fetchone.return_value = (1,)  # Simulate existing admin
    response = client.post('/register', data={
        'role': 'admin',
        'first_name': 'Super',
        'last_name': 'Admin',
        'email': 'admin@example.com',  # Duplicate
        'password': 'password123',
        'age': '50',
        'gender': 'Male',
        'department': 'HR',
        'contact': '0987654321'
    })
    assert response.status_code == 302

    # New edge case: Missing fields
    response = client.post('/register', data={
        'role': 'admin',
        'first_name': '',
        'last_name': '',
        'email': '',
        'password': '',
        'age': '',
        'gender': '',
        'department': '',
        'contact': ''
    })
    assert response.status_code == 302

# Expanded Test login for user with edge cases
@patch('app.check_password_hash', return_value=True)
@patch('app.sqlite3.connect')
def test_login_user(mock_connect, mock_check_password, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock user exists
    mock_cursor.fetchone.return_value = (1, 'John', 'Doe', 'john@example.com', 'hashed_pw', 'user')
    
    response = client.post('/login', data={
        'email': 'john@example.com',
        'password': 'password123',
        'role': 'user'
    })
    
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess['user_id'] == 1
        assert sess['role'] == 'user'

    # New edge case: Invalid password
    mock_check_password.return_value = False
    response = client.post('/login', data={
        'email': 'john@example.com',
        'password': 'wrongpassword',
        'role': 'user'
    })
    assert response.status_code == 302  # Should redirect with flash

    # New edge case: User not found
    mock_cursor.fetchone.return_value = None
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'password123',
        'role': 'user'
    })
    assert response.status_code == 302

    # New edge case: Missing fields
    response = client.post('/login', data={
        'email': '',
        'password': '',
        'role': 'user'
    })
    assert response.status_code == 302

# Expanded Test login for admin with edge cases
@patch('app.check_password_hash', return_value=True)
@patch('app.sqlite3.connect')
def test_login_admin(mock_connect, mock_check_password, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock admin exists
    mock_cursor.fetchone.return_value = (1, 'Admin', 'User', 'admin@example.com', 'hashed_pw')
    
    response = client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'password123',
        'role': 'admin'
    })
    
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess['user_id'] == 1
        assert sess['role'] == 'admin'

    # New edge case: Invalid password
    mock_check_password.return_value = False
    response = client.post('/login', data={
        'email': 'admin@example.com',
        'password': 'wrongpassword',
        'role': 'admin'
    })
    assert response.status_code == 302

    # New edge case: Admin not found
    mock_cursor.fetchone.return_value = None
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'password123',
        'role': 'admin'
    })
    assert response.status_code == 302

    # New edge case: Missing fields
    response = client.post('/login', data={
        'email': '',
        'password': '',
        'role': 'admin'
    })
    assert response.status_code == 302

# Test dashboard access without login
def test_dashboard_no_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302  # Redirect to login

# Test admin dashboard access as user
@patch('app.sqlite3.connect')
def test_admin_dashboard_as_user(mock_connect, client):
    with client.session_transaction() as sess:
        sess['role'] = 'user'
    
    response = client.get('/admin')
    assert response.status_code == 302  # Redirect

# Test add_info route
@patch('app.sqlite3.connect')
def test_add_info(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock user row as object
    mock_user = {
        'id': 1,
        'hypertension': 0,
        'heart_disease': 0,
        'avg_glucose_level': 90.0,
        'bmi': 22.0,
        'smoking_status': 1,
        'stroke': 0
    }
    mock_cursor.fetchone.return_value = mock_user
    
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    
    response = client.post('/add_info', data={
        'hypertension': 1,
        'heart_disease': 0,
        'avg_glucose_level': 100.0,
        'bmi': 25.0,
        'smoking_status': 1,
        'stroke': 0
    })
    
    assert response.status_code == 302
    mock_cursor.execute.assert_called()

# Test analyze route
@patch('app.history_db')
@patch('app.sqlite3.connect')
def test_analyze(mock_connect, mock_history_db, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock user row as a dict
    user_row = {
        'id': 1, 'first_name': 'John', 'last_name': 'Doe', 'age': 50, 'gender': 'Male',
        'work_type': 'Private', 'residence_type': 'Urban', 'ever_married': 'Yes',
        'bmi': 28.0, 'avg_glucose_level': 110.0, 'hypertension': 0, 'heart_disease': 1,
        'smoking_status': 1, 'stroke': 0
    }
    mock_cursor.fetchone.return_value = user_row
    
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    
    response = client.get('/analyze')
    assert response.status_code == 200
    mock_history_db.save.assert_called()

# Test feedback route
@patch('app.feedback_db')
@patch('app.sqlite3.connect')
def test_feedback(mock_connect, mock_feedback_db, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock fetchone to return a tuple
    mock_cursor.fetchone.return_value = (0.5,)
    
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    
    response = client.post('/feedback', data={
        'rating': 5,
        'comment': 'Great app!'
    })
    
    assert response.status_code == 302
    mock_feedback_db.save.assert_called()

# Test history route
@patch('app.history_db')
def test_history(mock_history_db, client):
    mock_row = MagicMock()
    mock_row.doc = {'user_id': 1, 'timestamp': '2023-01-01'}
    mock_history_db.view.return_value = [mock_row]
    
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    
    response = client.get('/history')
    assert response.status_code == 200

# Test admin delete user
@patch('app.sqlite3.connect')
def test_admin_delete_user(mock_connect, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
    
    response = client.post('/admin/user/1/delete')
    assert response.status_code == 302
    mock_cursor.execute.assert_called_with("DELETE FROM users WHERE id=?", (1,))

# Run tests with pytest
if __name__ == '__main__':
    pytest.main()
