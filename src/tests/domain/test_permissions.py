import pytest

from domain.auth import Permissions, Role

TEST_CASES = [
    pytest.param(
        Permissions.ALL,
        set(),
        {Role.ADMIN},
        {"some_field", "other_field"},
        True,
        id="Permissions.all works",
    ),
    pytest.param(
        Permissions.ALL,
        set(),
        {Role.TEAM_MEMBER},
        {"some_field", "other_field"},
        False,
        id="Empty set of fields fails for Team Member",
    ),
    pytest.param(
        Permissions.ALL,
        set(),
        {Role.ANONYMOUS},
        {"some_field", "other_field"},
        False,
        id="Empty set of fields fails for Anonymous",
    ),
    pytest.param(
        Permissions.ALL,
        {"some_field", "other_field"},
        {Role.TEAM_MEMBER},
        {"some_field", "other_field"},
        True,
        id="Can access when fields are allowed for role",
    ),
    pytest.param(
        Permissions.ALL,
        set(),
        {Role.TEAM_MEMBER, Role.ADMIN},
        {"some_field", "other_field"},
        True,
        id="Can access when user has multiple roles",
    ),
]


@pytest.mark.parametrize("admin,team_member, roles,fields,expected", TEST_CASES)
def test_permissions(admin, team_member, roles, fields, expected):
    permissions = Permissions(admin=admin, team_member=team_member)
    assert permissions.can_access_fields(roles=roles, fields=fields) == expected
