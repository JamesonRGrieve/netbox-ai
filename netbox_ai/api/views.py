# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST viewsets — automatic CRUD via ``NetBoxModelViewSet`` over the AI models."""
from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets
from ..models import (
    GatewayRoute,
    GatewayRouteTarget,
    GpuDevice,
    InferenceDeployment,
    ModelCatalog,
    ModelVariant,
)
from .serializers import (
    GatewayRouteSerializer,
    GatewayRouteTargetSerializer,
    GpuDeviceSerializer,
    InferenceDeploymentSerializer,
    ModelCatalogSerializer,
    ModelVariantSerializer,
)


class ModelCatalogViewSet(NetBoxModelViewSet):
    queryset = ModelCatalog.objects.prefetch_related("tags")
    serializer_class = ModelCatalogSerializer
    filterset_class = filtersets.ModelCatalogFilterSet


class ModelVariantViewSet(NetBoxModelViewSet):
    queryset = ModelVariant.objects.prefetch_related("model", "tags")
    serializer_class = ModelVariantSerializer
    filterset_class = filtersets.ModelVariantFilterSet


class GpuDeviceViewSet(NetBoxModelViewSet):
    queryset = GpuDevice.objects.prefetch_related("device", "gpu_hardware_object_type", "tags")
    serializer_class = GpuDeviceSerializer
    filterset_class = filtersets.GpuDeviceFilterSet


class InferenceDeploymentViewSet(NetBoxModelViewSet):
    queryset = InferenceDeployment.objects.prefetch_related(
        "service_instance", "variant", "gpus", "tags"
    )
    serializer_class = InferenceDeploymentSerializer
    filterset_class = filtersets.InferenceDeploymentFilterSet


class GatewayRouteViewSet(NetBoxModelViewSet):
    queryset = GatewayRoute.objects.prefetch_related("service_instance", "route_targets", "tags")
    serializer_class = GatewayRouteSerializer
    filterset_class = filtersets.GatewayRouteFilterSet


class GatewayRouteTargetViewSet(NetBoxModelViewSet):
    queryset = GatewayRouteTarget.objects.prefetch_related("route", "deployment", "tags")
    serializer_class = GatewayRouteTargetSerializer
    filterset_class = filtersets.GatewayRouteTargetFilterSet
