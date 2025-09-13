import pytest

from domain.auth import Permission, Role

TEST_CASES = [
    pytest.param(
        Role.ADMIN,
        Permission.ALL,
        {"some_field", "other_field"},
        True,
        id="Permissions.all works",
    ),
    pytest.param(
        Role.TEAM_MEMBER,
        set(),
        {"some_field", "other_field"},
        False,
        id="Empty set of fields fails for Team Member",
    ),
    pytest.param(
        Role.ANONYMOUS,
        set(),
        {"some_field", "other_field"},
        False,
        id="Empty set of fields fails for Anonymous",
    ),
    pytest.param(
        Role.TEAM_MEMBER,
        {"some_field", "other_field"},
        {"some_field", "other_field"},
        True,
        id="Can access when fields are allowed for role",
    ),
]


@pytest.mark.parametrize("role,allowed_fields,fields,expected", TEST_CASES)
def test_permissions(role, allowed_fields, fields, expected):
    permission = Permission(role=role, allowed_fields=allowed_fields)
    assert permission.can_access_fields(fields=fields) == expected
