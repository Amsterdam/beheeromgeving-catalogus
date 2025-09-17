from enum import StrEnum


class StrChoicesEnum(StrEnum):
    """Implemented choices method for easy conversion to tuples used in Django Models."""

    @classmethod
    def choices(cls, upper: bool = False):
        if upper:
            return tuple(
                (cls[item].value, item.upper().replace("_", " ")) for item in list(cls.__members__)
            )
        return tuple(
            (cls[item].value, item.lower().replace("_", " ").capitalize())
            for item in list(cls.__members__)
        )


class ProductType(StrChoicesEnum):
    DATAPRODUCT = "D"
    INFORMATIEPRODUCT = "I"


class Theme(StrChoicesEnum):
    BESTUUR = "B"
    CULTUUR_EN_RECREATIE = "CR"
    ECONOMIE = "E"
    FINANCIEN = "F"
    HUISVESTING = "H"
    INTERNATIONAAL = "I"
    LANDBOUW = "L"
    MIGRATIE_EN_INTEGRATIE = "MI"
    NATUUR_EN_MILIEU = "NM"
    ONDERWIJS_EN_WETENSCHAP = "OW"
    OPENBARE_ORDE_EN_VEILIGHEID = "OOV"
    RECHT = "R"
    RUIMTE_EN_INFRASTRUCTUUR = "RI"
    SOCIALE_ZEKERHEID = "SZ"
    VERKEER = "V"
    WERK = "W"
    ZORG_EN_GEZONDHEID = "ZG"


class Language(StrChoicesEnum):
    NEDERLANDS = "NL"
    ENGLISH = "EN"


class PublicationStatus(StrChoicesEnum):
    DRAFT = "D"
    IN_REVIEW = "R"
    APPROVED = "A"
    PUBLISHED = "P"
    EXPIRED = "E"


class ConfidentialityLevel(StrChoicesEnum):
    OPENBAAR = "O"
    INTERN = "I"
    VERTROUWELIJK = "V"
    GEHEIM = "G"


class DataServiceType(StrChoicesEnum):
    REST = "REST"
    WMS = "WMS"
    WFS = "WFS"


class DistributionType(StrChoicesEnum):
    DASHBOARD = "D"
    FOLDER = "M"
    FILE = "F"
    CUSTOM = "C"
    API = "A"


class CoordRefSystem(StrChoicesEnum):
    RD = "RD"
    ETRS89 = "ETRS89"
    WGS84 = "WGS84"
    UTM35S = "UTM35S"


class TimeUnit(StrChoicesEnum):
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"
