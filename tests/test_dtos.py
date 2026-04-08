import pytest
from django.http import QueryDict

from api.datatransferobjects import QueryParams, has_unpublished_changes_for_orm
from beheeromgeving.models import ProductPublishedSnapshot
from domain.product import enums


class TestQueryParams:
    @pytest.mark.parametrize(
        "query_string,expect,expect_filter,expect_query",
        [
            (
                "",
                QueryParams(),
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                None,
            ),
            ("publication_status=*", QueryParams(publication_status="*"), {}, None),
            (
                "name=bomen",
                QueryParams(name="bomen"),
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                None,
            ),
            (
                "language=EN",
                QueryParams(language="EN"),  # ty:ignore[invalid-argument-type]
                {
                    "language__in": [enums.Language.ENGLISH],
                    "publication_status": enums.PublicationStatus.PUBLISHED,
                },
                None,
            ),
            (
                "team=1&theme=NM,B",
                QueryParams(team="1", theme="NM,B"),  # ty:ignore[invalid-argument-type]
                {
                    "team_id__in": [1],
                    "themes__overlap": [enums.Theme.NATUUR_EN_MILIEU, enums.Theme.BESTUUR],
                    "publication_status": enums.PublicationStatus.PUBLISHED,
                },
                None,
            ),
            (
                "type=A&confidentiality=O",
                QueryParams(
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
                QueryParams(q="boom"),  # ty:ignore[unknown-argument]
                {"publication_status": enums.PublicationStatus.PUBLISHED},
                "boom",
            ),
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


@pytest.mark.django_db
class TestSnapshotDtoState:
    def test_has_unpublished_changes_false_without_snapshot(self, orm_product):
        ProductPublishedSnapshot.objects.filter(product_id=orm_product.id).delete()
        orm_product.refresh_from_db()
        assert has_unpublished_changes_for_orm(orm_product) is False

    def test_has_unpublished_changes_true_after_edit(self, orm_product):
        record = ProductPublishedSnapshot.objects.get(product_id=orm_product.id)
        ProductPublishedSnapshot.objects.filter(pk=record.pk).update(
            published_at=orm_product.last_updated
        )
        orm_product.description = "new value after publish"
        orm_product.save()
        orm_product.refresh_from_db()
        assert has_unpublished_changes_for_orm(orm_product) is True
