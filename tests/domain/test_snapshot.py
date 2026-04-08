"""Round-trip tests for published snapshots."""

import pytest

from beheeromgeving.models import Product, ProductPublishedSnapshot
from domain.product.repositories import ProductRepository
from domain.product.snapshot import snapshot_dict_to_product


@pytest.mark.django_db
def test_snapshot_roundtrip_matches_get_published(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    record = ProductPublishedSnapshot.objects.get(product_id=orm_product.pk)
    from_snap = snapshot_dict_to_product(record.snapshot)
    from_repo = repo.get_published(orm_product.pk)
    assert from_snap.id == from_repo.id
    assert from_snap.name == from_repo.name
    assert from_snap.description == from_repo.description
    assert len(from_snap.contracts) == len(from_repo.contracts)
    if from_snap.contracts:
        assert from_snap.contracts[0].name == from_repo.contracts[0].name


@pytest.mark.django_db
def test_clear_published_snapshot(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    repo.clear_published_snapshot(orm_product.pk)
    assert not ProductPublishedSnapshot.objects.filter(product_id=orm_product.pk).exists()


@pytest.mark.django_db
def test_sync_unpublished_clears(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    Product.objects.filter(pk=orm_product.pk).update(publication_status="D")
    repo.sync_published_snapshot(orm_product.pk)
    assert not ProductPublishedSnapshot.objects.filter(product_id=orm_product.pk).exists()


@pytest.mark.django_db
def test_product_to_snapshot_dict_has_version(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    record = ProductPublishedSnapshot.objects.get(product_id=orm_product.pk)
    assert record.snapshot["_snapshot_version"] == 1


@pytest.mark.django_db
def test_get_published_fallback_when_snapshot_cleared(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    repo.clear_published_snapshot(orm_product.pk)
    p = repo.get_published(orm_product.pk)
    assert p.name == orm_product.name


@pytest.mark.django_db
def test_get_published_by_name_fallback_when_snapshot_cleared(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    repo.clear_published_snapshot(orm_product.pk)
    p = repo.get_published_by_name("Bomen")
    assert p.name == "Bomen"


@pytest.mark.django_db
def test_get_published_accepts_string_refresh_period_from_snapshot(orm_product):
    repo = ProductRepository()
    repo.save_published_snapshot(orm_product.pk)
    record = ProductPublishedSnapshot.objects.get(product_id=orm_product.pk)
    record.snapshot["refresh_period"] = "3.MONTH"
    record.save(update_fields=["snapshot"])
    p = repo.get_published(orm_product.pk)
    assert p.refresh_period is not None
    assert p.refresh_period.to_string == "3.MONTH"


@pytest.mark.django_db
def test_get_published_raises_for_draft(orm_draft_product):
    from domain import exceptions

    repo = ProductRepository()
    with pytest.raises(exceptions.ObjectDoesNotExist):
        repo.get_published(orm_draft_product.pk)
