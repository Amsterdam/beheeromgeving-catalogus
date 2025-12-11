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
            ("order=-last_updated", QueryParams(order="-last_updated"), {}, None),
            ("q=boom", QueryParams(q="boom"), {}, "boom"),
        ],
    )
    def test_query_param_object(self, query_string, expect, expect_filter, expect_query):
        qd = QueryDict(query_string)
        qp = QueryParams(**qd.dict())
        assert qp == expect
        assert qp.filter == expect_filter
        assert qp.query == expect_query
