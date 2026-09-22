import pytest
from django.http import QueryDict
from pydantic import ValidationError

from api.datatransferobjects import ProductCreate, ProductList, ProductQueryParams, ProductUpdate
from beheeromgeving.models import DataContract, DataService, Distribution, Product
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
    @pytest.mark.django_db
    def test_product_summary_lists_alphabetically(self, orm_team):
        product = Product.objects.create(
            name="Bomen",
            description="bomen in Amsterdam",
            team=orm_team,
            data_steward="meneerboom@amsterdam.nl",
            language="NL",
            is_geo=True,
            schema_url="",
            type="D",
            themes=["NM"],
            refresh_period="3.MONTH",
            publication_status="P",
            publication_date="2024-01-01T00:00:00Z",
        )

        service_wms = DataService.objects.create(
            product=product,
            type="WMS",
            endpoint_url="https://api.data.amsterdam.nl/v1/bomen/wms",
        )
        DataService.objects.create(
            product=product,
            type="ATOM",
            endpoint_url="https://api.data.amsterdam.nl/v1/bomen/atom",
        )
        DataService.objects.create(
            product=product,
            type="REST",
            endpoint_url="https://api.data.amsterdam.nl/v1/bomen",
        )

        contract = DataContract.objects.create(
            product=product,
            publication_status="P",
            publication_date="2024-01-01T00:00:00Z",
            purpose="onderhoud van bomen",
            name="beheer bomen",
            privacy_level="NPI",
            scopes=["bomen_beheer"],
            confidentiality="I",
            start_date="2025-01-01",
            retainment_period=12,
            tables=["stamgegevens", "takgegevens"],
        )

        Distribution.objects.create(
            contract=contract,
            download_url="https://bomen.amsterdam.nl/beheer.geojson",
            format="geojson",
            type="F",
        )
        Distribution.objects.create(
            contract=contract,
            access_service=service_wms,
            type="A",
        )
        Distribution.objects.create(
            contract=contract,
            download_url="https://bomen.amsterdam.nl/beheer.csv",
            format="csv",
            type="F",
        )
        Distribution.objects.create(
            contract=contract,
            download_url="https://bomen.amsterdam.nl/beheer.avro",
            format="avro",
            type="F",
        )

        dto = ProductList.from_django(product)

        assert dto.summary == {
            "availability": ["API", "FILE"],
            "service_types": ["ATOM", "REST", "WMS"],
            "file_formats": ["AVRO", "CSV", "GEOJSON"],
        }

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
