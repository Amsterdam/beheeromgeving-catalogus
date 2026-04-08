from beheeromgeving.settings import *  # noqa: F403, F405

# The reason the settings are defined here, is to make them independent
# of the regular project sources. Otherwise, the project needs to have
# knowledge of the test framework.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Remove propagate=False so caplog can read those messages.
LOGGING = {
    **LOGGING,
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
    "loggers": {
        name: {
            **conf,
            "propagate": True,
        }
        for name, conf in LOGGING["handlers"].items()
    },
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Prevent tests to crash because of missing staticfiles manifests
WHITENOISE_MANIFEST_STRICT = False
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# App config
FEATURE_FLAG_USE_AUTH = True  # Tests rely on auth being enabled.
ADMIN_ROLE_NAME = "test_admin"

# Same EC key material as used by tests token builder (`kid=2aedafba-...`),
# so auth middleware can validate JWTs without requiring local .env JWKS vars.
_TEST_LOCAL_JWKS = (
    '{"keys":[{"kty":"EC","key_ops":["verify","sign"],"kid":"2aedafba-8170-4064-b704-ce92b7c89cc6",'
    '"crv":"P-256","x":"6r8PYwqfZbq_QzoMA4tzJJsYUIIXdeyPA27qTgEJCDw=","y":"Cf2clfAfFuuCB06NMfIat9ultkMyrMQO9Hd2H7O9ZVE=","d":"N1vu0UQUp0vLfaNeM0EDbl4quvvL6m_ltjoAXXzkI3U="}]}'
)

# Repo .env may set OAUTH_ALWAYS_OK; tests must exercise real JWT middleware behaviour.
DATAPUNT_AUTHZ = {
    **DATAPUNT_AUTHZ,
    "JWKS": DATAPUNT_AUTHZ.get("JWKS") or _TEST_LOCAL_JWKS,
    "ALWAYS_OK": False,
}
