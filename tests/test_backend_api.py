import os

import pytest
from fastapi.testclient import TestClient

pytest.importorskip('fastapi')

os.environ.setdefault('AUTH_SECRET_KEY', 'a' * 40)
os.environ.setdefault('DATABASE_URL', 'sqlite+pysqlite:///:memory:')

from backend.main import (
    app,
    get_current_active_user,
    require_admin,
    require_catalog_editor,
    require_catalog_manager,
    require_partner_access,
)


TEST_USER = {'id': 1, 'username': 'tester', 'role': 'admin', 'is_active': True}


@pytest.fixture(autouse=True)
def _authenticated_admin_override():
    overrides = {
        get_current_active_user: lambda: TEST_USER,
        require_admin: lambda: TEST_USER,
        require_catalog_editor: lambda: TEST_USER,
        require_catalog_manager: lambda: TEST_USER,
        require_partner_access: lambda: TEST_USER,
    }
    app.dependency_overrides.update(overrides)
    yield
    for dependency in overrides:
        app.dependency_overrides.pop(dependency, None)


def test_health_endpoint():
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_products_listing(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr('backend.main._fetch_products', lambda: [])

    response = client.get('/products')
    assert response.status_code == 200
    assert response.json() == []


def test_checkout_success(monkeypatch):
    client = TestClient(app)

    def fake_checkout(cart, username):
        assert cart == [{'id': 1, 'nom': 'Test', 'prix_vente': 2.5, 'tva': 5.5, 'qty': 1.0}]
        assert username == 'tester'
        return True, None, {'filename': 'ticket.pdf', 'content': b'binary'}

    monkeypatch.setattr('backend.main.process_sale_transaction', fake_checkout)
    monkeypatch.setattr(
        'backend.main._load_active_products_map',
        lambda product_ids: {
            1: {'id': 1, 'nom': 'Test', 'prix_vente': 2.5, 'tva': 5.5},
        },
    )

    response = client.post(
        '/pos/checkout',
        json={'cart': [{'id': 1, 'nom': 'Test', 'prix_vente': 2.5, 'tva': 5.5, 'qty': 1}], 'username': None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['success'] is True
    assert body['receipt_filename'] == 'ticket.pdf'
    assert body['receipt_base64'] is not None
    assert body['total_ht'] == 2.5
    assert body['total_ttc'] == 2.64


def test_product_update(monkeypatch):
    client = TestClient(app)
    called = {}

    def fake_update(product_id, changes, barcodes):
        called['product_id'] = product_id
        called['changes'] = changes
        called['barcodes'] = barcodes
        return {'fields_updated': len(changes)}

    monkeypatch.setattr('backend.main.update_catalog_entry', fake_update)

    response = client.patch(
        '/products/123',
        json={'nom': 'Nouveau nom', 'barcodes': ['1234567890123', '  ']},
    )

    assert response.status_code == 200
    assert called == {
        'product_id': 123,
        'changes': {'nom': 'Nouveau nom'},
        'barcodes': ['1234567890123'],
    }
    assert response.json()['status'] == 'updated'


def test_standard_user_cannot_update_product():
    client = TestClient(app)
    app.dependency_overrides[get_current_active_user] = lambda: {
        'id': 2,
        'username': 'standard',
        'role': 'standard',
        'is_active': True,
    }
    app.dependency_overrides.pop(require_catalog_editor, None)

    response = client.patch('/products/999', json={'nom': 'Interdit'})

    assert response.status_code == 403


def test_moderator_can_toggle_activation(monkeypatch):
    client = TestClient(app)
    called = {}

    def fake_update(product_id, changes, barcodes):
        called['product_id'] = product_id
        called['changes'] = changes
        called['barcodes'] = barcodes
        return {'fields_updated': len(changes)}

    monkeypatch.setattr('backend.main.update_catalog_entry', fake_update)

    app.dependency_overrides[get_current_active_user] = lambda: {
        'id': 3,
        'username': 'moderator',
        'role': 'moderator',
        'is_active': True,
    }
    app.dependency_overrides.pop(require_catalog_editor, None)

    response = client.patch('/products/77', json={'actif': False})

    assert response.status_code == 200
    assert called == {
        'product_id': 77,
        'changes': {'actif': False},
        'barcodes': None,
    }


def test_moderator_cannot_change_pricing():
    client = TestClient(app)

    app.dependency_overrides[get_current_active_user] = lambda: {
        'id': 3,
        'username': 'moderator',
        'role': 'moderator',
        'is_active': True,
    }
    app.dependency_overrides.pop(require_catalog_editor, None)

    response = client.patch('/products/77', json={'prix_vente': 10})

    assert response.status_code == 403


def test_standard_user_cannot_list_orders(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr('backend.api.orders.repository_list_orders', lambda: [])

    app.dependency_overrides[get_current_active_user] = lambda: {
        'id': 4,
        'username': 'standard',
        'role': 'standard',
        'is_active': True,
    }
    app.dependency_overrides.pop(require_partner_access, None)

    response = client.get('/orders')

    assert response.status_code == 403


def test_partner_can_list_orders(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr('backend.api.orders.repository_list_orders', lambda: [])

    app.dependency_overrides[get_current_active_user] = lambda: {
        'id': 5,
        'username': 'partner',
        'role': 'partner',
        'is_active': True,
    }
    app.dependency_overrides.pop(require_partner_access, None)

    response = client.get('/orders')

    assert response.status_code == 200
    assert response.json() == []
