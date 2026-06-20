# SPDX-License-Identifier: AGPL-3.0-or-later
"""FilterSets backing both the REST API and the UI list filters. FK filters are exposed by PK
(``<fk>_id``) and, where there is a natural key, by name."""
import django_filters
from dcim.models import Device
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from netbox_services.models import ServiceInstance

from .choices import (
    DeploymentStatusChoices,
    DTypeChoices,
    KVCacheQuantChoices,
    ModalityChoices,
    ModelSourceTypeChoices,
    QuantizationChoices,
)
from .models import (
    GatewayRoute,
    GatewayRouteTarget,
    GpuDevice,
    InferenceDeployment,
    ModelCatalog,
    ModelVariant,
)


class ModelCatalogFilterSet(NetBoxModelFilterSet):
    modality = django_filters.MultipleChoiceFilter(choices=ModalityChoices)
    source_type = django_filters.MultipleChoiceFilter(choices=ModelSourceTypeChoices)

    class Meta:
        model = ModelCatalog
        fields = ["id", "name", "display_name", "architecture", "parameter_count", "license"]

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(display_name__icontains=value)
            | Q(architecture__icontains=value)
            | Q(description__icontains=value)
        )


class ModelVariantFilterSet(NetBoxModelFilterSet):
    model_id = django_filters.ModelMultipleChoiceFilter(
        field_name="model", queryset=ModelCatalog.objects.all(), label="Model (ID)"
    )
    model = django_filters.ModelMultipleChoiceFilter(
        field_name="model__name", to_field_name="name", queryset=ModelCatalog.objects.all(), label="Model (name)"
    )
    quant = django_filters.MultipleChoiceFilter(choices=QuantizationChoices)

    class Meta:
        model = ModelVariant
        fields = ["id", "recommended_context"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(model__name__icontains=value) | Q(quant__icontains=value))


class GpuDeviceFilterSet(NetBoxModelFilterSet):
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device", queryset=Device.objects.all(), label="Host (ID)"
    )

    class Meta:
        model = GpuDevice
        fields = ["id", "index", "interconnect_group"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(device__name__icontains=value) | Q(interconnect_group__icontains=value))


class InferenceDeploymentFilterSet(NetBoxModelFilterSet):
    service_instance_id = django_filters.ModelMultipleChoiceFilter(
        field_name="service_instance", queryset=ServiceInstance.objects.all(), label="Backend (ID)"
    )
    variant_id = django_filters.ModelMultipleChoiceFilter(
        field_name="variant", queryset=ModelVariant.objects.all(), label="Variant (ID)"
    )
    status = django_filters.MultipleChoiceFilter(choices=DeploymentStatusChoices)
    dtype = django_filters.MultipleChoiceFilter(choices=DTypeChoices)
    kv_cache_quant = django_filters.MultipleChoiceFilter(choices=KVCacheQuantChoices)

    class Meta:
        model = InferenceDeployment
        fields = ["id", "served_model_name", "tensor_parallel", "pipeline_parallel", "max_model_len"]

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(served_model_name__icontains=value) | Q(variant__model__name__icontains=value)
        )


class GatewayRouteFilterSet(NetBoxModelFilterSet):
    service_instance_id = django_filters.ModelMultipleChoiceFilter(
        field_name="service_instance", queryset=ServiceInstance.objects.all(), label="Gateway (ID)"
    )
    status = django_filters.MultipleChoiceFilter(choices=DeploymentStatusChoices)

    class Meta:
        model = GatewayRoute
        fields = ["id", "public_name", "rate_limit"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(public_name__icontains=value))


class GatewayRouteTargetFilterSet(NetBoxModelFilterSet):
    route_id = django_filters.ModelMultipleChoiceFilter(
        field_name="route", queryset=GatewayRoute.objects.all(), label="Route (ID)"
    )
    deployment_id = django_filters.ModelMultipleChoiceFilter(
        field_name="deployment", queryset=InferenceDeployment.objects.all(), label="Deployment (ID)"
    )

    class Meta:
        model = GatewayRouteTarget
        fields = ["id", "order", "weight"]

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(route__public_name__icontains=value) | Q(deployment__served_model_name__icontains=value)
        )
