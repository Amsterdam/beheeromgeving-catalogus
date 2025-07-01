from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DataContractViewSet,
    DataTeamViewSet,
    health,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"datateams", DataTeamViewSet, basename="datateams")
router.register(r"datacontracts", DataContractViewSet, basename="datacontracts")

urlpatterns = [path("pulse", health)] + router.urls

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
