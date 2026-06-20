# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST router registration."""
from netbox.api.routers import NetBoxRouter

from . import views

app_name = "netbox_ai"

router = NetBoxRouter()
router.register("model-catalog", views.ModelCatalogViewSet)
router.register("model-variants", views.ModelVariantViewSet)
router.register("gpu-devices", views.GpuDeviceViewSet)
router.register("inference-deployments", views.InferenceDeploymentViewSet)
router.register("gateway-routes", views.GatewayRouteViewSet)
router.register("gateway-route-targets", views.GatewayRouteTargetViewSet)

urlpatterns = router.urls
