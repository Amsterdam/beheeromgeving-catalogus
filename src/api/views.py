from pydantic import ValidationError
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api import datatransferobjects as dtos
from domain import exceptions
from domain.auth import AuthorizationRepository, AuthorizationService, authorize
from domain.product import ProductRepository, ProductService
from domain.team import TeamRepository, TeamService


@api_view(["GET"])
def health(request):
    return Response({"status": "OK"})


class ExceptionHandlerMixin:
    def handle_exception(self, e):
        match e:
            case ValidationError():
                return Response(
                    status=400,
                    data=e.json(include_url=False, include_input=False, include_context=False),
                )
            case exceptions.ValidationError():
                return Response(status=400, data=e.message)
            case exceptions.IllegalOperation():
                return Response(status=400, data=e.message)
            case exceptions.NotAuthorized():
                return Response(status=401, data=e.message)
            case exceptions.ObjectDoesNotExist():
                return Response(status=404, data=e.message)
            case exceptions.DomainException():
                return Response(status=500, data=e.message)
        raise e


class TeamViewSet(ExceptionHandlerMixin, ViewSet):
    service: TeamService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        auth_service = AuthorizationService(AuthorizationRepository())
        authorize.set_auth_service(auth_service)
        self.service = TeamService(repo=TeamRepository())

    def _validate_dto(self, data, dto_model=dtos.Team):
        # Raises if data is invalid
        return dto_model(**data)

    def list(self, _request):
        teams = self.service.get_teams()
        data = dtos.to_response_object(teams)
        return Response(data, status=200)

    def retrieve(self, _request, pk=None):
        team = self.service.get_team(int(pk))
        return Response(dtos.to_response_object(team), status=200)

    def create(self, request):
        team_dto = self._validate_dto(request.data)
        team_id = self.service.create_team(
            data=team_dto.model_dump(), scopes=request.get_token_scopes
        )
        return Response(status=201, data=team_id)

    def partial_update(self, request, pk=None):
        team_dto = self._validate_dto(request.data, dtos.TeamPartial)
        self.service.update_team(
            team_id=int(pk),
            data=team_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        return Response(status=200)

    def destroy(self, request, pk=None):
        self.service.delete_team(int(pk), scopes=request.get_token_scopes)
        return Response(status=204)


class ProductViewSet(ExceptionHandlerMixin, ViewSet):
    service: ProductService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        auth_service = AuthorizationService(AuthorizationRepository())
        authorize.set_auth_service(auth_service)
        self.service = ProductService(repo=ProductRepository())

    def _validate_dto(self, data, dto_type=dtos.ProductDetail):
        # Raises if data is invalid
        return dto_type(**data)

    def list(self, _request):
        products = self.service.get_products()
        data = dtos.to_response_object(products)
        return Response(data, status=200)

    def retrieve(self, _request, pk=None):
        product = self.service.get_product(int(pk))
        return Response(dtos.to_response_object(product), status=200)

    def create(self, request):
        product_dto = self._validate_dto(request.data)
        # ignore contracts/service as these should be created through their own endpoint
        product = self.service.create_product(
            data=product_dto.model_dump(exclude=["contracts", "services"]),
            scopes=request.get_token_scopes,
        )
        return Response(dtos.to_response_object(product), status=201)

    def partial_update(self, request, pk=None):
        product_dto = self._validate_dto(request.data, dto_type=dtos.ProductUpdate)

        # ignore contracts/service as these should be created through their own endpoint
        product = self.service.update_product(
            product_id=int(pk),
            data=product_dto.model_dump(exclude_unset=True, exclude=["contracts", "services"]),
            scopes=request.get_token_scopes,
        )
        return Response(dtos.to_response_object(product), status=200)

    def destroy(self, request, pk=None):
        self.service.delete_product(product_id=int(pk), scopes=request.get_token_scopes)
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="contracts", url_name="contracts-list")
    def contracts_list(self, _request, pk=None):
        contracts = self.service.get_contracts(int(pk))
        data = dtos.to_response_object(contracts)
        return Response(data, status=200)

    @contracts_list.mapping.post
    def create_contract(self, request, pk=None):
        contract_dto = self._validate_dto(request.data, dtos.DataContract)
        contract = self.service.create_contract(
            product_id=int(pk), data=contract_dto.model_dump(), scopes=request.get_token_scopes
        )
        data = dtos.to_response_object(contract)
        return Response(data, status=201)

    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)",
        url_name="contract-detail",
    )
    def contract_detail(self, _request, pk=None, contract_id=None):
        contract = self.service.get_contract(int(pk), int(contract_id))
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @contract_detail.mapping.patch
    def update_contract(self, request, pk=None, contract_id=None):
        contract_dto = self._validate_dto(request.data, dtos.DataContract)
        contract = self.service.update_contract(
            product_id=int(pk),
            contract_id=int(contract_id),
            data=contract_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @contract_detail.mapping.delete
    def delete_contract(self, request, pk=None, contract_id=None):
        self.service.delete_contract(
            product_id=int(pk), contract_id=int(contract_id), scopes=request.get_token_scopes
        )
        return Response(status=204)

    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)/distributions",
        url_name="distributions-list",
    )
    def distributions_list(self, request, pk=None, contract_id=None):
        distributions = self.service.get_distributions(
            product_id=int(pk), contract_id=int(contract_id)
        )
        data = dtos.to_response_object(distributions)
        return Response(data, status=200)

    @distributions_list.mapping.post
    def create_distribution(self, request, pk=None, contract_id=None):
        distribution_dto = self._validate_dto(request.data, dto_type=dtos.Distribution)
        distribution = self.service.create_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            data=distribution_dto.model_dump(),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=201)

    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)/distributions/(?P<distribution_id>[^/.]+)",
        url_name="distributions-detail",
    )
    def distribution_detail(self, request, pk=None, contract_id=None, distribution_id=None):
        distribution = self.service.get_distribution(
            product_id=int(pk), contract_id=int(contract_id), distribution_id=int(distribution_id)
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=200)

    @distribution_detail.mapping.patch
    def update_distribution(self, request, pk=None, contract_id=None, distribution_id=None):
        distribution_dto = self._validate_dto(request.data, dtos.Distribution)
        distribution = self.service.update_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            distribution_id=int(distribution_id),
            data=distribution_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=200)

    @distribution_detail.mapping.delete
    def delete_distribution(self, request, pk=None, contract_id=None, distribution_id=None):
        self.service.delete_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            distribution_id=int(distribution_id),
            scopes=request.get_token_scopes,
        )
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="services", url_name="services-list")
    def services_list(self, _request, pk=None):
        services = self.service.get_services(int(pk))
        data = dtos.to_response_object(services)
        return Response(data, status=200)

    @services_list.mapping.post
    def create_service(self, request, pk=None):
        service_dto = self._validate_dto(request.data, dtos.DataService)
        service = self.service.create_service(
            product_id=int(pk),
            data=service_dto.model_dump(),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(service)
        return Response(data, status=201)

    @action(
        detail=True,
        methods=["get"],
        url_path="services/(?P<service_id>[^/.]+)",
        url_name="service-detail",
    )
    def service_detail(self, _request, pk=None, service_id=None):
        service = self.service.get_service(int(pk), int(service_id))
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @service_detail.mapping.patch
    def update_service(self, request, pk=None, service_id=None):
        service_dto = self._validate_dto(request.data, dtos.DataService)
        service = self.service.update_service(
            product_id=int(pk),
            service_id=int(service_id),
            data=service_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @service_detail.mapping.delete
    def delete_servie(self, request, pk=None, service_id=None):
        self.service.delete_service(
            product_id=int(pk), service_id=int(service_id), scopes=request.get_token_scopes
        )
        return Response(status=204)
