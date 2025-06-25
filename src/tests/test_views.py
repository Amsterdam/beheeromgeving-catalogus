def test_health(api_client):
    response = api_client.get("/pulse")
    assert response.status_code == 200
    assert response.data == {"status": "OK"}
