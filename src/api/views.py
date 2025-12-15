from drf_spectacular.utils import OpenApiParameter, extend_schema
from pydantic import ValidationError
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api import datatransferobjects as dtos
from api.pagination import NotFound, Pagination
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
            case NotFound():
                return Response(status=404, data=e.detail)
            case exceptions.DomainException():
                return Response(status=500, data=e.message)
        raise e


auth_service: AuthorizationService
product_service: ProductService
team_service: TeamService
is_initialized = False


def initialize():
    """
    Instantiate all necessary services. ViewSets are instantiated for each request,
    so we share the same services throughout the lifecycle of the application.
    """
    global auth_service, product_service, team_service
    auth_service = AuthorizationService(AuthorizationRepository())
    authorize.set_auth_service(auth_service)
    product_service = ProductService(repo=ProductRepository())
    team_service = TeamService(repo=TeamRepository())


class TeamViewSet(ExceptionHandlerMixin, ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global is_initialized
        if not is_initialized:
            initialize()
            is_initialized = True

    def _validate_dto[M: dtos.BaseModel](self, data, dto_model: type[M] = dtos.TeamCreate) -> M:
        # Raises if data is invalid
        return dto_model(**data)

    @extend_schema(responses={200: dtos.TeamList})
    def list(self, _request):
        teams = team_service.get_teams()
        data = dtos.to_response_object(teams)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.Team})
    def retrieve(self, _request, pk=None):
        team = team_service.get_team(int(pk))
        return Response(dtos.to_response_object(team), status=200)

    @extend_schema(responses={200: dtos.TeamCreate})
    def create(self, request):
        team_dto = self._validate_dto(request.data)
        team_id = team_service.create_team(
            data=team_dto.model_dump(), scopes=request.get_token_scopes
        )
        return Response(status=201, data=team_id)

    @extend_schema(responses={200: dtos.TeamPartial})
    def partial_update(self, request, pk=None):
        team_dto = self._validate_dto(request.data, dtos.TeamPartial)
        team_service.update_team(
            team_id=int(pk),
            data=team_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        return Response(status=200)

    @extend_schema()
    def destroy(self, request, pk=None):
        team_service.delete_team(int(pk), scopes=request.get_token_scopes)
        return Response(status=204)


class ProductViewSet(ExceptionHandlerMixin, ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global is_initialized
        if not is_initialized:
            initialize()
            is_initialized = True

    def _validate_dto[M: dtos.BaseModel](self, data, dto_type: type[M] = dtos.ProductCreate) -> M:
        # Raises if data is invalid
        return dto_type(**data)

    @extend_schema(
        responses={200: dtos.ProductList},
        parameters=[
            OpenApiParameter("name", description="Query on full product name."),
            OpenApiParameter(
                "q",
                description="Query on a search string found in product name/description or "
                "underlying contract name/description. If multiple words are entered only "
                "one of those words needs to be present.",
            ),
            OpenApiParameter(
                "page", description="Page number (1-indexed) for the paginated results.", default=1
            ),
            OpenApiParameter(
                "pagesize",
                description="Page size for the paginated results. Max = 100.",
                default=10,
            ),
            OpenApiParameter("team", description="Filter on team (name)."),
            OpenApiParameter("theme", description="Filter on theme(s), comma-separated list."),
            OpenApiParameter("confidentiality", description="Filter on confidentiality level."),
            OpenApiParameter(
                "type", description="Filter on distribution type, comma-separated list."
            ),
            OpenApiParameter("language", description="Filter on language."),
        ],
    )
    def list(self, request):
        params = self._validate_dto(request.query_params.dict(), dto_type=dtos.QueryParams)
        if params.name:
            product = product_service.get_product_by_name(params.name)
            data = dtos.to_response_object(product)
            return Response(data, status=200)

        products = product_service.get_products(
            query=params.query,
            filter=params.filter,
            order=params.order,
        )

        data = dtos.to_response_object(products)
        pagination = Pagination()
        paginated_data = pagination.paginate(data, request)
        return pagination.get_paginated_response(paginated_data)

    @extend_schema(responses={200: dtos.ProductDetail})
    def retrieve(self, _request, pk=None):
        product = product_service.get_product(int(pk))
        return Response(dtos.to_response_object(product), status=200)

    @extend_schema(responses={200: dtos.ProductCreate})
    def create(self, request):
        product_dto = self._validate_dto(request.data)
        # ignore contracts/service as these should be created through their own endpoint
        product = product_service.create_product(
            data=product_dto.model_dump(exclude={"contracts", "services"}),
            scopes=request.get_token_scopes,
        )
        return Response(dtos.to_response_object(product), status=201)

    @extend_schema(responses={200: dtos.ProductUpdate})
    def partial_update(self, request, pk=None):
        product_dto = self._validate_dto(request.data, dto_type=dtos.ProductUpdate)
        # ignore contracts/service as these should be updated through their own endpoint
        product = product_service.update_product(
            product_id=int(pk),
            data=product_dto.model_dump(exclude_unset=True, exclude={"contracts", "services"}),
            scopes=request.get_token_scopes,
        )
        return Response(dtos.to_response_object(product), status=200)

    @extend_schema()
    def destroy(self, request, pk=None):
        product_service.delete_product(product_id=int(pk), scopes=request.get_token_scopes)
        return Response(status=204)

    @extend_schema(responses={200: dtos.SetState})
    @action(detail=True, methods=["post"], url_path="set-state", url_name="publication_status")
    def set_state(self, request, pk=None):
        state_dto = self._validate_dto(request.data, dto_type=dtos.SetState)

        updated_product = product_service.update_publication_status(
            product_id=int(pk),
            data=state_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(updated_product)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.DataContractList})
    @action(detail=True, methods=["get"], url_path="contracts", url_name="contracts-list")
    def contracts_list(self, _request, pk: str):
        contracts = product_service.get_contracts(int(pk))
        data = dtos.to_response_object(contracts)
        return Response(data, status=200)

    @extend_schema(responses={201: dtos.DataContractCreateOrUpdate})
    @contracts_list.mapping.post
    def create_contract(self, request, pk: str):
        contract_dto = self._validate_dto(request.data, dtos.DataContractCreateOrUpdate)
        contract = product_service.create_contract(
            product_id=int(pk), data=contract_dto.model_dump(), scopes=request.get_token_scopes
        )
        data = dtos.to_response_object(contract)
        return Response(data, status=201)

    @extend_schema(responses={200: dtos.DataContract})
    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)",
        url_name="contract-detail",
    )
    def contract_detail(self, _request, pk=None, contract_id=None):
        contract = product_service.get_contract(int(pk), int(contract_id))
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.DataContractCreateOrUpdate})
    @contract_detail.mapping.patch
    def update_contract(self, request, pk=None, contract_id=None):
        contract_dto = self._validate_dto(request.data, dtos.DataContractCreateOrUpdate)
        contract = product_service.update_contract(
            product_id=int(pk),
            contract_id=int(contract_id),
            data=contract_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(contract)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.SetState})
    @action(
        detail=True,
        methods=["post"],
        url_path="contracts/(?P<contract_id>[^/.]+)/set-state",
        url_name="contract_publication_status",
    )
    def set_state_contract(self, request, pk=None, contract_id=None):
        state_dto = self._validate_dto(request.data, dto_type=dtos.SetState)

        updated_contract = product_service.update_contract_publication_status(
            product_id=int(pk),
            contract_id=int(contract_id),
            data=state_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(updated_contract)
        return Response(data, status=200)

    @extend_schema()
    @contract_detail.mapping.delete
    def delete_contract(self, request, pk=None, contract_id=None):
        product_service.delete_contract(
            product_id=int(pk), contract_id=int(contract_id), scopes=request.get_token_scopes
        )
        return Response(status=204)

    @extend_schema(responses={200: dtos.Distribution})
    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)/distributions",
        url_name="distributions-list",
    )
    def distributions_list(self, request, pk=None, contract_id=None):
        distributions = product_service.get_distributions(
            product_id=int(pk), contract_id=int(contract_id)
        )
        data = dtos.to_response_object(distributions)
        return Response(data, status=200)

    @extend_schema(responses={201: dtos.DistributionCreateOrUpdate})
    @distributions_list.mapping.post
    def create_distribution(self, request, pk=None, contract_id=None):
        distribution_dto = self._validate_dto(
            request.data, dto_type=dtos.DistributionCreateOrUpdate
        )
        distribution = product_service.create_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            data=distribution_dto.model_dump(),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=201)

    @extend_schema(responses={200: dtos.Distribution})
    @action(
        detail=True,
        methods=["get"],
        url_path="contracts/(?P<contract_id>[^/.]+)/distributions/(?P<distribution_id>[^/.]+)",
        url_name="distributions-detail",
    )
    def distribution_detail(self, request, pk=None, contract_id=None, distribution_id=None):
        distribution = product_service.get_distribution(
            product_id=int(pk), contract_id=int(contract_id), distribution_id=int(distribution_id)
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.DistributionCreateOrUpdate})
    @distribution_detail.mapping.patch
    def update_distribution(self, request, pk=None, contract_id=None, distribution_id=None):
        distribution_dto = self._validate_dto(request.data, dtos.DistributionCreateOrUpdate)
        distribution = product_service.update_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            distribution_id=int(distribution_id),
            data=distribution_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(distribution)
        return Response(data, status=200)

    @extend_schema()
    @distribution_detail.mapping.delete
    def delete_distribution(self, request, pk=None, contract_id=None, distribution_id=None):
        product_service.delete_distribution(
            product_id=int(pk),
            contract_id=int(contract_id),
            distribution_id=int(distribution_id),
            scopes=request.get_token_scopes,
        )
        return Response(status=204)

    @extend_schema(responses={200: dtos.DataService})
    @action(detail=True, methods=["get"], url_path="services", url_name="services-list")
    def services_list(self, _request, pk=None):
        services = product_service.get_services(int(pk))
        data = dtos.to_response_object(services)
        return Response(data, status=200)

    @extend_schema(responses={201: dtos.DataServiceCreateOrUpdate})
    @services_list.mapping.post
    def create_service(self, request, pk=None):
        service_dto = self._validate_dto(request.data, dtos.DataServiceCreateOrUpdate)
        service = product_service.create_service(
            product_id=int(pk),
            data=service_dto.model_dump(),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(service)
        return Response(data, status=201)

    @extend_schema(responses={200: dtos.DataService})
    @action(
        detail=True,
        methods=["get"],
        url_path="services/(?P<service_id>[^/.]+)",
        url_name="service-detail",
    )
    def service_detail(self, _request, pk=None, service_id=None):
        service = product_service.get_service(int(pk), int(service_id))
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @extend_schema(responses={200: dtos.DataServiceCreateOrUpdate})
    @service_detail.mapping.patch
    def update_service(self, request, pk=None, service_id=None):
        service_dto = self._validate_dto(request.data, dtos.DataServiceCreateOrUpdate)
        service = product_service.update_service(
            product_id=int(pk),
            service_id=int(service_id),
            data=service_dto.model_dump(exclude_unset=True),
            scopes=request.get_token_scopes,
        )
        data = dtos.to_response_object(service)
        return Response(data, status=200)

    @extend_schema()
    @service_detail.mapping.delete
    def delete_service(self, request, pk=None, service_id=None):
        product_service.delete_service(
            product_id=int(pk), service_id=int(service_id), scopes=request.get_token_scopes
        )
        return Response(status=204)


@extend_schema(responses={200: dtos.MeDetail})
@api_view(["GET"])
def me(request):
    try:
        params = dtos.QueryParams(**request.query_params.dict())
    except ValidationError as e:
        return Response(
            status=400, data=e.json(include_url=False, include_input=False, include_context=False)
        )
    team_service = TeamService(repo=TeamRepository())
    product_service = ProductService(repo=ProductRepository())
    scopes = request.get_token_scopes
    teams = team_service.get_teams_from_scopes(scopes)
    products = product_service.get_products(
        teams=teams, order=params.order or ("last_updated", True)
    )
    product_data = dtos.to_response_object(products, dto_type="me")
    pagination = Pagination()
    try:
        product_data = pagination.paginate(product_data, request)
    except NotFound as e:
        return Response(status=404, data=e.detail)
    data = {
        "teams": dtos.to_response_object(teams, dto_type="me"),
        "products": pagination.get_paginated_response_body(product_data),
    }
    return Response(data, status=200)
