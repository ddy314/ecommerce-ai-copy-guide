from backend.app import create_app
from backend.services.auth_service import hash_password, verify_password


def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_login_uses_standard_jwt_and_protected_route():
    api = client()
    response = api.post(
        "/api/auth/login",
        json={"username": "user", "password": "user123", "role": "user"},
    )

    assert response.status_code == 200
    token = response.get_json()["token"]
    assert token.count(".") == 2

    current_user = api.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.get_json()["user"]["username"] == "user"


def test_password_hash_uses_werkzeug_scrypt():
    password_hash = hash_password("secure-password")

    assert password_hash.startswith("scrypt:")
    assert verify_password("secure-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_cors_is_limited_to_configured_origins():
    api = client()
    response = api.options(
        "/api/capabilities",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
