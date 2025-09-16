import time

from authorization_django import jwks
from jwcrypto.jwt import JWT


def build_jwt_token(scopes, subject="test@example.com"):
    now = int(time.time())

    kid = "2aedafba-8170-4064-b704-ce92b7c89cc6"
    key = jwks.get_keyset().get_key(kid)
    token = JWT(
        header={"alg": "ES256", "kid": kid},
        claims={"iat": now, "exp": now + 30, "scopes": scopes, "sub": subject},
    )
    token.make_signed_token(key)
    return token.serialize()
