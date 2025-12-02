from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularSwaggerView,
    SpectacularYAMLAPIView,
)
from rest_framework.routers import DefaultRouter

from api.views import ProductViewSet, TeamViewSet, health, me

router = DefaultRouter(trailing_slash=False)
router.register(r"teams", TeamViewSet, basename="teams")
router.register(r"products", ProductViewSet, basename="products")

urlpatterns = [
    path("pulse", health),
    path("me", me),
    path(
        "schema",
        SpectacularSwaggerView.as_view(url_name="schema-json"),
        name="swagger-ui",
    ),
    path("openapi.json", SpectacularJSONAPIView.as_view(), name="schema-json"),
    path("openapi.yaml", SpectacularYAMLAPIView.as_view(), name="schema-yaml"),
] + router.urls

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
