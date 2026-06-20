# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST serializers — the contract the Semaphore renderer + catalog seeder read. FKs into core
``dcim`` and the sibling ``netbox_services`` plugin nest those plugins' own serializers; the GPU
hardware GFK mirrors the ``ServiceInstance.parent`` read pattern; derived figures
(``vram_total_gb``, ``estimated_vram_gb``) are read-only."""
from dcim.api.serializers import DeviceSerializer
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from netbox.api.fields import ContentTypeField, SerializedPKRelatedField
from netbox.api.serializers import NetBoxModelSerializer
from netbox_services.api.serializers import ServiceInstanceSerializer
from rest_framework import serializers

from ..models import (
    GatewayRoute,
    GatewayRouteTarget,
    GpuDevice,
    InferenceDeployment,
    ModelCatalog,
    ModelVariant,
)

_META = ["tags", "custom_fields", "created", "last_updated"]


class ModelCatalogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:modelcatalog-detail")

    class Meta:
        model = ModelCatalog
        fields = ["id", "url", "display", "name", "display_name", "description", "architecture",
                  "parameter_count", "modality", "source_type", "source", "license", "default_context",
                  "max_context", *_META]
        brief_fields = ["id", "url", "display", "name", "display_name"]


class ModelVariantSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:modelvariant-detail")
    model = ModelCatalogSerializer(nested=True)

    class Meta:
        model = ModelVariant
        fields = ["id", "url", "display", "model", "quant", "weights_vram_gb", "recommended_context", *_META]
        brief_fields = ["id", "url", "display", "model", "quant"]


class GpuDeviceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:gpudevice-detail")
    device = DeviceSerializer(nested=True)
    gpu_hardware_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False, allow_null=True)
    gpu_hardware = serializers.SerializerMethodField(read_only=True)
    vram_total_gb = serializers.FloatField(read_only=True, allow_null=True)
    reserved_vram_gb = serializers.FloatField(read_only=True)

    class Meta:
        model = GpuDevice
        fields = ["id", "url", "display", "device", "index", "gpu_hardware_object_type",
                  "gpu_hardware_object_id", "gpu_hardware", "vram_total_gb", "vram_total_gb_override",
                  "reserved_vram_gb", "interconnect_group", "description", *_META]
        brief_fields = ["id", "url", "display", "device", "index"]

    @extend_schema_field(serializers.JSONField(allow_null=True))
    def get_gpu_hardware(self, obj):
        if obj.gpu_hardware is None:
            return None
        request = self.context.get("request")
        url = obj.gpu_hardware.get_absolute_url()
        return {
            "id": obj.gpu_hardware.pk,
            "display": str(obj.gpu_hardware),
            "url": request.build_absolute_uri(url) if request else url,
        }


class InferenceDeploymentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:inferencedeployment-detail")
    service_instance = ServiceInstanceSerializer(nested=True)
    variant = ModelVariantSerializer(nested=True)
    gpus = SerializedPKRelatedField(
        queryset=GpuDevice.objects.all(), serializer=GpuDeviceSerializer, nested=True, required=False, many=True
    )
    estimated_vram_gb = serializers.FloatField(read_only=True)
    estimated_vram_total_gb = serializers.FloatField(read_only=True)

    class Meta:
        model = InferenceDeployment
        fields = ["id", "url", "display", "served_model_name", "service_instance", "variant", "gpus",
                  "status", "tensor_parallel", "pipeline_parallel", "gpu_memory_utilization", "max_model_len",
                  "kv_cache_quant", "dtype", "extra_args", "estimated_vram_gb", "estimated_vram_total_gb",
                  "description", *_META]
        brief_fields = ["id", "url", "display", "served_model_name", "status"]


class GatewayRouteSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:gatewayroute-detail")
    service_instance = ServiceInstanceSerializer(nested=True)
    # The ordered targets are embedded read-only (the renderer reads a route + its fallbacks in one
    # payload); they are created/edited via the GatewayRouteTarget endpoint. A SerializerMethodField
    # (not a nested GatewayRouteTargetSerializer) avoids the route↔target serializer reference cycle.
    targets = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GatewayRoute
        fields = ["id", "url", "display", "public_name", "service_instance", "status", "rate_limit",
                  "targets", "description", *_META]
        brief_fields = ["id", "url", "display", "public_name"]

    @extend_schema_field(serializers.ListField(child=serializers.JSONField()))
    def get_targets(self, obj):
        return [
            {
                "id": t.pk,
                "deployment_id": t.deployment_id,
                "served_model_name": t.deployment.served_model_name,
                "order": t.order,
                "weight": t.weight,
            }
            for t in obj.route_targets.select_related("deployment").all()
        ]


class GatewayRouteTargetSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_ai-api:gatewayroutetarget-detail")
    route = GatewayRouteSerializer(nested=True)
    deployment = InferenceDeploymentSerializer(nested=True)

    class Meta:
        model = GatewayRouteTarget
        fields = ["id", "url", "display", "route", "deployment", "order", "weight", *_META]
        brief_fields = ["id", "url", "display", "deployment", "order"]
