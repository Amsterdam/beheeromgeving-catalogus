"""Serialize/deserialize domain Product trees for published snapshots."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from domain.product import enums
from domain.product.objects import DataContract, DataService, Distribution, Product, RefreshPeriod

SNAPSHOT_VERSION = 1


def product_to_snapshot_dict(product: Product) -> dict[str, Any]:
    """Convert a domain Product to JSON-storable dict."""
    payload = _to_json_safe(product)
    payload["_snapshot_version"] = SNAPSHOT_VERSION
    return payload


def snapshot_dict_to_product(data: dict[str, Any]) -> Product:
    """Restore domain Product from snapshot dict."""
    raw = {k: v for k, v in data.items() if k != "_snapshot_version"}
    return _product_from_dict(raw)


def _to_json_safe(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj):
        return {k: _to_json_safe(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    return obj


def _e(enum_cls: type, value: Any):
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


def _product_from_dict(d: dict[str, Any]) -> Product:
    contracts = [_contract_from_dict(c) for c in d.get("contracts") or []]
    services = [_service_from_dict(s) for s in d.get("services") or []]
    refresh_period = _refresh_period_from_any(d.get("refresh_period"))
    return Product(
        id=d.get("id"),
        name=d.get("name"),
        description=d.get("description"),
        language=_e(enums.Language, d.get("language")) if d.get("language") else None,
        is_geo=d.get("is_geo"),
        crs=_e(enums.CoordRefSystem, d.get("crs")) if d.get("crs") else None,
        schema_url=d.get("schema_url"),
        type=_e(enums.ProductType, d.get("type")) if d.get("type") else None,
        contracts=contracts,
        themes=[_e(enums.Theme, t) for t in d["themes"]] if d.get("themes") else None,
        last_updated=_parse_dt(d.get("last_updated")),
        created_at=_parse_dt(d.get("created_at")),
        refresh_period=refresh_period,
        publication_status=_e(enums.PublicationStatus, d.get("publication_status"))
        if d.get("publication_status")
        else None,
        owner=d.get("owner"),
        contact_email=d.get("contact_email"),
        data_steward=d.get("data_steward"),
        services=services,
        sources=list(d.get("sources") or []),
        sinks=list(d.get("sinks") or []),
        team_id=d["team_id"],
    )


def _enum_key_or_value(enum_cls: type, raw: str) -> str:
    """Accept enum member name (MONTH) or value for RefreshPeriod.from_dict."""
    if raw in enum_cls.__members__:
        return raw
    for name, member in enum_cls.__members__.items():
        if member.value == raw:
            return name
    return raw


def _refresh_period_from_any(raw: Any) -> RefreshPeriod | None:
    if not raw:
        return None
    if isinstance(raw, dict):
        return RefreshPeriod.from_dict(
            {"frequency": raw["frequency"], "unit": _enum_key_or_value(enums.TimeUnit, raw["unit"])}
        )
    if isinstance(raw, str):
        return RefreshPeriod.from_string(raw)
    return None


def _contract_from_dict(c: dict[str, Any]) -> DataContract:
    distros = [_distribution_from_dict(x) for x in c.get("distributions") or []]
    return DataContract(
        id=c.get("id"),
        publication_status=_e(enums.PublicationStatus, c.get("publication_status"))
        if c.get("publication_status")
        else None,
        purpose=c.get("purpose"),
        name=c.get("name"),
        description=c.get("description"),
        last_updated=_parse_dt(c.get("last_updated")),
        privacy_level=_e(enums.PrivacyLevel, c.get("privacy_level"))
        if c.get("privacy_level")
        else None,
        scopes=c.get("scopes"),
        confidentiality=_e(enums.ConfidentialityLevel, c.get("confidentiality"))
        if c.get("confidentiality")
        else None,
        start_date=_parse_date(c.get("start_date")),
        retainment_period=c.get("retainment_period"),
        distributions=distros,
        tables=c.get("tables"),
        schema_url=c.get("schema_url"),
    )


def _distribution_from_dict(d: dict[str, Any]) -> Distribution:
    rp = d.get("refresh_period")
    refresh_period = None
    if isinstance(rp, dict):
        refresh_period = RefreshPeriod.from_dict(
            {"frequency": rp["frequency"], "unit": _enum_key_or_value(enums.TimeUnit, rp["unit"])}
        )
    crs_val = d.get("crs")
    crs = None
    if crs_val:
        crs = [_e(enums.CoordRefSystem, x) for x in crs_val]
    return Distribution(
        id=d.get("id"),
        access_service_id=d.get("access_service_id"),
        access_url=d.get("access_url"),
        download_url=d.get("download_url"),
        format=d.get("format"),
        filename=d.get("filename"),
        type=_e(enums.DistributionType, d.get("type")) if d.get("type") else None,
        refresh_period=refresh_period,
        crs=crs,
    )


def _service_from_dict(s: dict[str, Any]) -> DataService:
    return DataService(
        id=s.get("id"),
        type=_e(enums.DataServiceType, s.get("type")) if s.get("type") else None,
        endpoint_url=s.get("endpoint_url"),
    )


def _parse_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    return None


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return None
