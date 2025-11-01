import os

import pytest
from fastapi.testclient import TestClient

pytest.importorskip('fastapi')

os.environ.setdefault('AUTH_SECRET_KEY', 'a' * 40)
os.environ.setdefault('DATABASE_URL', 'sqlite+pysqlite:///:memory:')

from backend.main import app, get_current_active_user, require_admin


TEST_USER = {'id': 1, 'username': 'tester', 'role': 'admin', 'is_active': True}


@pytest.fixture(autouse=True)
def _authenticated_admin_override():
    app.dependency_overrides[get_current_active_user] = lambda: TEST_USER
    app.dependency_overrides[require_admin] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(require_admin, None)


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
