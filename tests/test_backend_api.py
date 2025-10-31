import pytest

pytest.importorskip('fastapi')

from fastapi.testclient import TestClient

from backend.main import app


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
        assert cart == [{'id': 1, 'nom': 'Test', 'prix_vente': 2.5, 'tva': 5.5, 'qty': 1}]
        assert username == 'api_user'
        return True, None, {'filename': 'ticket.pdf', 'content': b'binary'}

    monkeypatch.setattr('backend.main.process_sale_transaction', fake_checkout)

    response = client.post(
        '/pos/checkout',
        json={'cart': [{'id': 1, 'nom': 'Test', 'prix_vente': 2.5, 'tva': 5.5, 'qty': 1}], 'username': None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['success'] is True
    assert body['receipt_filename'] == 'ticket.pdf'
    assert body['receipt_base64'] is not None


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
