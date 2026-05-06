import pytest
from django.http import QueryDict
from pydantic import ValidationError

from api.datatransferobjects import ProductCreate, ProductQueryParams, ProductUpdate
from domain.product import enums


class TestQueryParams:
    @pytest.mark.parametrize(
        "query_string,expect,expect_filter,expect_query",
        [
            (
                "",
                ProductQueryParams(),
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                None,
            ),
            ("publication_status=*", ProductQueryParams(publication_status="*"), {}, None),
            (
                "name=bomen",
                ProductQueryParams(name="bomen"),
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                None,
            ),
            (
                "language=EN",
                ProductQueryParams(language="EN"),  # ty:ignore[invalid-argument-type]
                {
                    "language__in": [enums.Language.ENGLISH],
                    "publication_status": enums.PublicationStatus.PUBLISHED,
                },
                None,
            ),
            (
                "team=1&theme=NM,B",
                ProductQueryParams(team="1", theme="NM,B"),  # ty:ignore[invalid-argument-type]
                {
                    "team_id__in": [1],
                    "themes__overlap": [enums.Theme.NATUUR_EN_MILIEU, enums.Theme.BESTUUR],
                    "publication_status": enums.PublicationStatus.PUBLISHED,
                },
                None,
            ),
            (
                "type=A&confidentiality=O",
                ProductQueryParams(
                    type="A",  # ty:ignore[invalid-argument-type]
                    confidentiality=enums.ConfidentialityLevel.OPENBAAR,  # ty:ignore[invalid-argument-type]
                ),
                {
                    "contracts__distributions__type__in": [enums.DistributionType.API],
                    "contracts__confidentiality__in": [enums.ConfidentialityLevel.OPENBAAR],
                    "publication_status": enums.PublicationStatus.PUBLISHED,
                },
                None,
            ),
            (
                "q=boom",
                ProductQueryParams(q="boom"),
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                "boom",
            ),
        ],
    )
    def test_query_param_object(self, query_string, expect, expect_filter, expect_query):
        qd = QueryDict(query_string)
        qp = ProductQueryParams(**qd.dict())
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
        qp = ProductQueryParams(**qd.dict())
        assert qp.order == expected_order


class TestProductDTOValidation:
    def test_product_create_access_url_allowed_for_information_product(self):
        dto = ProductCreate(
            team_id=1,
            type=enums.ProductType.INFORMATIEPRODUCT,
            access_url="https://example.com/report",
        )
        assert dto.access_url == "https://example.com/report"

    def test_product_create_access_url_rejected_for_non_information_product(self):
        with pytest.raises(
            ValidationError,
            match="access_url is only allowed when the product is an information product",
        ):
            ProductCreate(
                team_id=1,
                type=enums.ProductType.DATAPRODUCT,
                access_url="https://example.com/report",
            )

    def test_product_update_access_url_allowed_for_information_product(self):
        dto = ProductUpdate(
            type=enums.ProductType.INFORMATIEPRODUCT,
            access_url="https://example.com/report",
        )
        assert dto.access_url == "https://example.com/report"

    def test_product_update_access_url_rejected_when_type_is_dataproduct(self):
        with pytest.raises(
            ValidationError,
            match="access_url is only allowed when the product is an information product",
        ):
            ProductUpdate(
                access_url="https://example.com/report", type=enums.ProductType.DATAPRODUCT
            )
