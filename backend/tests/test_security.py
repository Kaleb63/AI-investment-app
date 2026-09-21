from backend.services.security_service import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_password_hashing_and_access_token_round_trip():
    hashed = hash_password("a-very-long-test-password")
    assert hashed != "a-very-long-test-password"
    assert verify_password("a-very-long-test-password", hashed)
    assert not verify_password("wrong-password", hashed)

    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_sensitive_values_are_encrypted_at_rest():
    encrypted = encrypt_secret("plaid-access-token")
    assert encrypted != "plaid-access-token"
    assert decrypt_secret(encrypted) == "plaid-access-token"
