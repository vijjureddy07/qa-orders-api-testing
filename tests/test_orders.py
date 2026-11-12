"""Each test gets its own database: order and state isolation is intentional."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture()
def setup(tmp_path):
    path = tmp_path / 'orders.sqlite3'
    return TestClient(create_app(path)), path

@pytest.fixture()
def valid_order():
    return {"customer": "Asha Rao", "sku": "MOUSE-01", "quantity": 2}

def test_health_returns_ok(setup):
    client, _ = setup
    assert client.get('/health').json() == {"status": "ok"}

def test_create_order_status_and_price(setup, valid_order):
    client, _ = setup
    response = client.post('/orders', json=valid_order)
    assert response.status_code == 201
    assert response.json()['total'] == 1598
    assert response.json()['status'] == 'pending'

def test_missing_customer_is_422(setup, valid_order):
    client, _ = setup
    del valid_order['customer']
    assert client.post('/orders', json=valid_order).status_code == 422

@pytest.mark.parametrize('quantity', [0, -1, 11])
def test_quantity_boundaries_invalid(setup, valid_order, quantity):
    client, _ = setup
    valid_order['quantity'] = quantity
    assert client.post('/orders', json=valid_order).status_code == 422

@pytest.mark.parametrize('quantity', [1, 10])
def test_quantity_boundaries_valid(setup, valid_order, quantity):
    client, _ = setup
    valid_order['quantity'] = quantity
    assert client.post('/orders', json=valid_order).status_code == 201

def test_unknown_sku_returns_400(setup, valid_order):
    client, _ = setup
    valid_order['sku'] = 'UNKNOWN'
    assert client.post('/orders', json=valid_order).status_code == 400

def test_read_missing_order_returns_404(setup):
    client, _ = setup
    assert client.get('/orders/9999').status_code == 404

def test_status_workflow_and_conflict(setup, valid_order):
    client, _ = setup
    order_id = client.post('/orders', json=valid_order).json()['id']
    assert client.patch(f'/orders/{order_id}/status', json={'status': 'shipped'}).status_code == 409
    assert client.patch(f'/orders/{order_id}/status', json={'status': 'packed'}).status_code == 200
    assert client.patch(f'/orders/{order_id}/status', json={'status': 'shipped'}).status_code == 200
    assert client.patch(f'/orders/{order_id}/status', json={'status': 'cancelled'}).status_code == 409

def test_filtering_and_db_matches_api(setup, valid_order):
    client, db_path = setup
    pending = client.post('/orders', json=valid_order).json()
    other = client.post('/orders', json={'customer': 'Kiran', 'sku': 'CABLE-02', 'quantity': 1}).json()
    client.patch(f"/orders/{other['id']}/status", json={'status': 'cancelled'})
    api_orders = client.get('/orders', params={'status': 'pending'}).json()
    assert len(api_orders) == 1 and api_orders[0]['id'] == pending['id']
    with sqlite3.connect(db_path) as db:
        row = db.execute('SELECT total,status FROM orders WHERE id=?', (pending['id'],)).fetchone()
        assert row == (1598, 'pending')

def test_invalid_status_filter_400(setup):
    client, _ = setup
    assert client.get('/orders?status=delivered').status_code == 400

def test_whitespace_only_customer_is_rejected(setup, valid_order):
    client, _ = setup
    valid_order['customer'] = '   '
    assert client.post('/orders', json=valid_order).status_code == 422
