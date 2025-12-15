import pytest
from django.http import QueryDict

from api.datatransferobjects import QueryParams
from domain.product import enums


class TestQueryParams:
    @pytest.mark.parametrize(
        "query_string,expect,expect_filter,expect_query",
        [
            ("", QueryParams(), {}, None),
            ("name=bomen", QueryParams(name="bomen"), {}, None),
            (
                "language=EN",
                QueryParams(language="EN"),
                {"language": enums.Language.ENGLISH},
                None,
            ),
            (
                "team=1&theme=NM,B",
                QueryParams(team=1, theme="NM,B"),
                {"team": 1, "theme": [enums.Theme.NATUUR_EN_MILIEU, enums.Theme.BESTUUR]},
                None,
            ),
            (
                "type=A&confidentiality=O",
                QueryParams(
                    type="A",
                    confidentiality=enums.ConfidentialityLevel.OPENBAAR,
                ),
                {
                    "type": [enums.DistributionType.API],
                    "confidentiality": enums.ConfidentialityLevel.OPENBAAR,
                },
                None,
            ),
            ("q=boom", QueryParams(q="boom"), {}, "boom"),
        ],
    )
    def test_query_param_object(self, query_string, expect, expect_filter, expect_query):
        qd = QueryDict(query_string)
        qp = QueryParams(**qd.dict())
        assert qp == expect
        assert qp.filter == expect_filter
        assert qp.query == expect_query

    @pytest.mark.parametrize(
        "query_string,expected_order",
        [
            ("order=last_updated", ("last_updated", False)),
            ("order=-last_updated", ("last_updated", True)),
            ("order=name", ("name", False)),
            ("order=-name", ("name", True)),
        ],
    )
    def test_query_param_order(self, query_string, expected_order):
        qd = QueryDict(query_string)
        qp = QueryParams(**qd.dict())
        assert qp.order == expected_order
