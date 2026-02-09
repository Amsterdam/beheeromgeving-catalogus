from domain.product.enums import TimeUnit

REFRESH_MAP: dict[str, dict[str, int | TimeUnit]] = {
    "Hoogstens 1x per jaar": {"frequency": 1, "unit": TimeUnit.YEAR},
    "Dagelijks (werkdagen)": {"frequency": 5, "unit": TimeUnit.WEEK},
    "Per halfjaar": {"frequency": 2, "unit": TimeUnit.YEAR},
    "Weekelijks (op maandag)": {"frequency": 1, "unit": TimeUnit.WEEK},
    "Elk kwartaal": {"frequency": 4, "unit": TimeUnit.YEAR},
    "Per kwartaal": {"frequency": 4, "unit": TimeUnit.YEAR},
    "Iedere werkdag": {"frequency": 5, "unit": TimeUnit.WEEK},
    "Eenmalig": {"frequency": 0, "unit": TimeUnit.YEAR},
}

FREQUENCY_MAP = {
    "Een": 1,
    "1": 1,
    "3": 3,
    "Twee": 2,
    "Drie": 3,
    "Vier": 4,
    "Dagelijks": 1,
    "Maandelijks": 1,
    "Wekelijks": 1,
    "Weekelijks": 1,
    "Jaarlijks": 1,
    "Jaarlijks,": 1,
}
UNIT_MAP = {
    "maand": TimeUnit.MONTH,
    "dag": TimeUnit.DAY,
    "uur": TimeUnit.HOUR,
    "jaar": TimeUnit.YEAR,
    "week": TimeUnit.WEEK,
    "Dagelijks": TimeUnit.DAY,
    "Wekelijks": TimeUnit.WEEK,
    "Maandelijks": TimeUnit.MONTH,
    "Jaarlijks": TimeUnit.YEAR,
}
