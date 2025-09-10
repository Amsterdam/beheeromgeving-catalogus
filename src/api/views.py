from pydantic import ValidationError
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api import datatransferobjects as dtos
from domain import exceptions
from domain.product.repositories import ProductRepository, TeamRepository
from domain.product.services import ProductService, TeamService


@api_view(["GET"])
def health(request):
    return Response({"status": "OK"})


class TeamViewSet(ViewSet):
    service: TeamService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TeamService(repo=TeamRepository())

    def _validate_dto(self, data, dto_model=dtos.Team):
        # Raises if data is invalid
        return dto_model(**data)

    def list(self, _request):
        teams = self.service.get_teams()
        data = dtos.to_response_object(teams)
        return Response(data, status=200)

    def retrieve(self, _request, pk=None):
        try:
            team = self.service.get_team(int(pk))
        except exceptions.ObjectDoesNotExist as e:
            return Response(status=404, data=str(e.message))

        return Response(dtos.to_response_object(team), status=200)

    def create(self, request):
        try:
            team_dto = self._validate_dto(request.data)
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )

        team_id = self.service.create_team(team_dto.model_dump())
        return Response(status=201, data=team_id)

    def partial_update(self, request, pk=None):
        try:
            team_dto = self._validate_dto(request.data, dtos.TeamPartial)
            self.service.update_team(int(pk), team_dto.model_dump(exclude_unset=True))
        except exceptions.IllegalOperation as e:
            return Response(status=400, data=str(e.message))
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        return Response(status=200)

    def destroy(self, request, pk=None):
        try:
            self.service.delete_team(int(pk))
        except exceptions.ObjectDoesNotExist:
            return Response(f"Team with id {pk} does not exist", status=404)
        return Response(status=204)


class ProductViewSet(ViewSet):
    service: ProductService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = ProductService(repo=ProductRepository())

    def _validate_dto(self, data, dto_type=dtos.ProductDetail):
        # Raises if data is invalid
        return dto_type(**data)

    def list(self, request):
        products = self.service.get_products()
        data = dtos.to_response_object(products)
        return Response(data, status=200)

    def retrieve(self, request, pk=None):
        try:
            product = self.service.get_product(int(pk))
            return Response(dtos.to_response_object(product), status=200)
        except exceptions.ObjectDoesNotExist:
            return Response(status=404)

    def create(self, request):
        try:
            product_dto = self._validate_dto(request.data)
            # ignore contracts/service as these should be created through their own endpoint
            product = self.service.create_product(
                product_dto.model_dump(exclude=["contracts", "services"])
            )
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        except exceptions.IllegalOperation as e:
            return Response(status=400, data=str(e.message))
        return Response(dtos.to_response_object(product), status=201)

    def partial_update(self, request, pk=None):
        try:
            product_dto = self._validate_dto(request.data)

            # ignore contracts/service as these should be created through their own endpoint
            self.service.update_product(
                int(pk),
                product_dto.model_dump(exclude_unset=True, exclude=["contracts", "services"]),
            )
        except exceptions.IllegalOperation as e:
            return Response(status=400, data=str(e.message))
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        except exceptions.ObjectDoesNotExist:
            return Response(f"Product with id {pk} does not exist", status=404)
        return Response(status=200)

    def destroy(self, request, pk=None):
        try:
            self.service.delete_product(int(pk))
        except exceptions.ObjectDoesNotExist:
            return Response(f"Product with id {pk} does not exist", status=404)
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="contracts", url_name="contracts-list")
    def contracts_list(self, request, pk=None):
        try:
            contracts = self.service.get_contracts(int(pk))
        except exceptions.ObjectDoesNotExist:
            return Response(f"Project with id {pk} does not exist.", status=404)
        data = dtos.to_response_object(contracts)
        return Response(data, status=200)

    @contracts_list.mapping.post
    def create_contract(self, request, pk=None):
        try:
            contract_dto = self._validate_dto(request.data, dtos.DataContract)
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        contract = self.service.create_contract(int(pk), contract_dto.model_dump())
        data = dtos.to_response_object(contract)
        return Response(data, status=201)

    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)",
        url_name="contract-detail",
    )
    def contract_detail(self, request, pk=None, contract_id=None):
        try:
            contract = self.service.get_contract(int(pk), int(contract_id))
        except (exceptions.ObjectDoesNotExist, StopIteration):
            return Response(
                f"Contract with id {contract_id} does not exist on Product {pk}", status=404
            )
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @contract_detail.mapping.patch
    def update_contract(self, request, pk=None, contract_id=None):
        try:
            contract_dto = self._validate_dto(request.data, dtos.DataContract)
            contract = self.service.update_contract(
                int(pk), int(contract_id), contract_dto.model_dump(exclude_unset=True)
            )
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        except exceptions.IllegalOperation as e:
            return Response(status=400, data=str(e.message))
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @contract_detail.mapping.delete
    def delete_contract(self, request, pk=None, contract_id=None):
        self.service.delete_contract(int(pk), int(contract_id))
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="services", url_name="services-list")
    def services_list(self, request, pk=None):
        try:
            services = self.service.get_services(int(pk))
        except exceptions.ObjectDoesNotExist:
            return Response(f"Project with id {pk} does not exist.", status=404)
        data = dtos.to_response_object(services)
        return Response(data, status=200)

    @services_list.mapping.post
    def create_service(self, request, pk=None):
        try:
            service_dto = self._validate_dto(request.data, dtos.DataService)
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        service = self.service.create_service(int(pk), service_dto.model_dump())
        data = dtos.to_response_object(service)
        return Response(data, status=201)

    @action(
        detail=True,
        methods=["get"],
        url_path="services/(?P<service_id>[^/.]+)",
        url_name="service-detail",
    )
    def service_detail(self, request, pk=None, service_id=None):
        try:
            service = self.service.get_service(int(pk), int(service_id))
        except (exceptions.ObjectDoesNotExist, StopIteration):
            return Response(
                f"Service with id {service_id} does not exist on Product with id {pk}", status=404
            )
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @service_detail.mapping.patch
    def update_service(self, request, pk=None, service_id=None):
        try:
            service_dto = self._validate_dto(request.data, dtos.DataService)
            service = self.service.update_service(
                int(pk), int(service_id), service_dto.model_dump(exclude_unset=True)
            )
        except ValidationError as e:
            return Response(
                status=400,
                data=e.json(include_url=False, include_input=False, include_context=False),
            )
        except exceptions.IllegalOperation as e:
            return Response(status=400, data=str(e.message))
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @service_detail.mapping.delete
    def delete_servie(self, request, pk=None, service_id=None):
        self.service.delete_service(int(pk), int(service_id))
        return Response(status=204)
