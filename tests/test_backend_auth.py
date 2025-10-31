from fastapi.testclient import TestClient

from backend.main import app, create_access_token, get_password_hash


def _authorization_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_success(monkeypatch):
    client = TestClient(app)

    password = 'super-secret'
    hashed = get_password_hash(password)

    monkeypatch.setattr(
        'backend.main.fetch_user_by_username',
        lambda username: {
            'id': 1,
            'username': username,
            'email': 'admin@example.test',
            'full_name': 'Admin Test',
            'role': 'admin',
            'hashed_password': hashed,
            'is_active': True,
            'created_at': None,
            'updated_at': None,
        },
    )

    response = client.post('/auth/login', json={'username': 'admin', 'password': password})
    assert response.status_code == 200
    payload = response.json()
    assert 'access_token' in payload
    assert payload['user']['role'] == 'admin'


def test_login_rejects_inactive_account(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        'backend.main.fetch_user_by_username',
        lambda username: {
            'id': 2,
            'username': username,
            'email': 'user@example.test',
            'full_name': 'User',
            'role': 'standard',
            'hashed_password': get_password_hash('password'),
            'is_active': False,
            'created_at': None,
            'updated_at': None,
        },
    )

    response = client.post('/auth/login', json={'username': 'user', 'password': 'password'})
    assert response.status_code == 403


def test_list_users_requires_admin(monkeypatch):
    client = TestClient(app)

    # Authenticate as a standard user
    monkeypatch.setattr(
        'backend.main.fetch_user_by_username',
        lambda username: {
            'id': 5,
            'username': username,
            'email': 'user@example.test',
            'full_name': 'User',
            'role': 'standard',
            'is_active': True,
            'created_at': None,
            'updated_at': None,
        },
    )

    token = create_access_token({'sub': 'user', 'role': 'standard'})
    response = client.get('/users', headers=_authorization_header(token))
    assert response.status_code == 403


def test_admin_can_list_users(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        'backend.main.fetch_user_by_username',
        lambda username: {
            'id': 1,
            'username': username,
            'email': 'admin@example.test',
            'full_name': 'Admin Test',
            'role': 'admin',
            'is_active': True,
            'created_at': None,
            'updated_at': None,
        },
    )

    monkeypatch.setattr(
        'backend.main.repository_list_users',
        lambda: [
            {
                'id': 1,
                'username': 'admin',
                'email': 'admin@example.test',
                'full_name': 'Admin Test',
                'role': 'admin',
                'is_active': True,
                'created_at': None,
                'updated_at': None,
            },
            {
                'id': 2,
                'username': 'user',
                'email': 'user@example.test',
                'full_name': 'User Test',
                'role': 'standard',
                'is_active': True,
                'created_at': None,
                'updated_at': None,
            },
        ],
    )

    token = create_access_token({'sub': 'admin', 'role': 'admin'})
    response = client.get('/users', headers=_authorization_header(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['username'] == 'admin'


def test_update_user_prevents_removing_last_admin(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        'backend.main.fetch_user_by_username',
        lambda username: {
            'id': 1,
            'username': username,
            'email': 'admin@example.test',
            'full_name': 'Admin',
            'role': 'admin',
            'is_active': True,
            'created_at': None,
            'updated_at': None,
        },
    )

    monkeypatch.setattr(
        'backend.main.fetch_user_by_id',
        lambda user_id: {
            'id': user_id,
            'username': 'admin',
            'email': 'admin@example.test',
            'full_name': 'Admin',
            'role': 'admin',
            'is_active': True,
            'created_at': None,
            'updated_at': None,
        },
    )

    monkeypatch.setattr('backend.main.count_active_admins', lambda exclude_user_id=None: 0)
    # Prevent database call during the test
    monkeypatch.setattr('backend.main.update_user_record', lambda user_id, payload: None)

    token = create_access_token({'sub': 'admin', 'role': 'admin'})
    response = client.patch(
        '/users/1',
        headers=_authorization_header(token),
        json={'role': 'standard'},
    )
    assert response.status_code == 400
    assert 'administrateur actif' in response.json()['detail']
