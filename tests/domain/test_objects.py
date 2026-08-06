import pytest

from domain.exceptions import ValidationError
from domain.product import DataContract, DataService, Distribution, Product, enums


class TestProductValidator:
    def test_product_can_update_to_information_type_with_no_contracts(self):
        product = Product(
            team_id=1, contracts=[], publication_status=enums.PublicationStatus.DRAFT
        )

        # Regression: this used to crash with IndexError when contracts == []
        assert product.validate.can_update({"type": "I"}) is True

    def test_product_can_update_to_information_type_with_single_contract_single_distribution(self):
        product = Product(
            team_id=1,
            publication_status=enums.PublicationStatus.DRAFT,
            contracts=[DataContract(distributions=[Distribution()])],
        )

        # Regression: this used to incorrectly raise because it checked ">= 1".
        assert product.validate.can_update({"type": "I"}) is True

    def test_product_cannot_update_to_information_type_with_multiple_contracts(self):
        product = Product(
            team_id=1,
            publication_status=enums.PublicationStatus.DRAFT,
            contracts=[DataContract(), DataContract()],
        )

        with pytest.raises(
            ValidationError,
            match="Information product cannot have multiple contracts or distributions.",
        ):
            product.validate.can_update({"type": "I"})


class TestProduct:
    def test_summary_sorts_and_deduplicates_distribution_and_service_metadata(self):
        product = Product(
            team_id=1,
            contracts=[
                DataContract(
                    distributions=[
                        Distribution(type=enums.DistributionType.API),
                        Distribution(type=enums.DistributionType.FILE, format="csv"),
                        Distribution(type=enums.DistributionType.FILE, format="geojson"),
                        Distribution(type=enums.DistributionType.FILE, format="csv"),
                        Distribution(type=enums.DistributionType.API, format="json"),
                        Distribution(format="xml"),
                    ]
                )
            ],
            services=[
                DataService(type=enums.DataServiceType.WMS),
                DataService(type=enums.DataServiceType.ATOM),
                DataService(type=enums.DataServiceType.WMS),
            ],
        )

        assert product.summary == {
            "availability": ["API", "FILE"],
            "service_types": ["ATOM", "WMS"],
            "file_formats": ["CSV", "GEOJSON"],
        }

    def test_product_cannot_update_to_information_type_with_multiple_distributions(self):
        product = Product(
            team_id=1,
            publication_status=enums.PublicationStatus.DRAFT,
            contracts=[DataContract(distributions=[Distribution(), Distribution()])],
        )

        with pytest.raises(
            ValidationError,
            match="Information product cannot have multiple contracts or distributions.",
        ):
            product.validate.can_update({"type": "I"})
