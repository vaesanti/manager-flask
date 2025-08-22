# tests/test_app.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_homepage(client):
    """Testa se a página inicial carrega com sucesso"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"DayZ" in response.data  # Verifica se aparece algo relacionado ao painel
