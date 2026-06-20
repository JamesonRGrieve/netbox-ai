# SPDX-License-Identifier: AGPL-3.0-or-later
"""NetBox list tables for the AI catalog + placement models. Derived figures (``vram_total_gb``,
``estimated_vram_gb``) surface as plain columns off the model properties."""
import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from .models import (
    GatewayRoute,
    GatewayRouteTarget,
    GpuDevice,
    InferenceDeployment,
    ModelCatalog,
    ModelVariant,
)


class ModelCatalogTable(NetBoxTable):
    name = tables.Column(linkify=True)
    modality = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_ai:modelcatalog_list")

    class Meta(NetBoxTable.Meta):
        model = ModelCatalog
        fields = ("pk", "id", "name", "display_name", "architecture", "parameter_count", "modality",
                  "source_type", "source", "license", "default_context", "max_context", "tags",
                  "created", "last_updated")
        default_columns = ("name", "display_name", "architecture", "parameter_count", "modality")


class ModelVariantTable(NetBoxTable):
    model = tables.Column(linkify=True)
    quant = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_ai:modelvariant_list")

    class Meta(NetBoxTable.Meta):
        model = ModelVariant
        fields = ("pk", "id", "model", "quant", "weights_vram_gb", "recommended_context", "tags",
                  "created", "last_updated")
        default_columns = ("model", "quant", "weights_vram_gb", "recommended_context")


class GpuDeviceTable(NetBoxTable):
    device = tables.Column(linkify=True)
    index = tables.Column(linkify=True)
    gpu_hardware = tables.Column(linkify=False, verbose_name="GPU Hardware")
    vram_total_gb = tables.Column(verbose_name="VRAM Total (GiB)", orderable=False)
    reserved_vram_gb = tables.Column(verbose_name="VRAM Reserved (GiB)", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_ai:gpudevice_list")

    class Meta(NetBoxTable.Meta):
        model = GpuDevice
        fields = ("pk", "id", "device", "index", "gpu_hardware", "vram_total_gb", "vram_total_gb_override",
                  "reserved_vram_gb", "interconnect_group", "tags", "created", "last_updated")
        default_columns = ("device", "index", "gpu_hardware", "vram_total_gb", "reserved_vram_gb",
                           "interconnect_group")


class InferenceDeploymentTable(NetBoxTable):
    served_model_name = tables.Column(linkify=True)
    service_instance = tables.Column(linkify=True)
    variant = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    estimated_vram_gb = tables.Column(verbose_name="Est. VRAM/GPU (GiB)", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_ai:inferencedeployment_list")

    class Meta(NetBoxTable.Meta):
        model = InferenceDeployment
        fields = ("pk", "id", "served_model_name", "service_instance", "variant", "status",
                  "tensor_parallel", "pipeline_parallel", "gpu_memory_utilization", "max_model_len",
                  "kv_cache_quant", "dtype", "estimated_vram_gb", "tags", "created", "last_updated")
        default_columns = ("served_model_name", "service_instance", "variant", "status",
                           "tensor_parallel", "pipeline_parallel", "estimated_vram_gb")


class GatewayRouteTable(NetBoxTable):
    public_name = tables.Column(linkify=True)
    service_instance = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_ai:gatewayroute_list")

    class Meta(NetBoxTable.Meta):
        model = GatewayRoute
        fields = ("pk", "id", "public_name", "service_instance", "status", "rate_limit", "tags",
                  "created", "last_updated")
        default_columns = ("public_name", "service_instance", "status", "rate_limit")


class GatewayRouteTargetTable(NetBoxTable):
    route = tables.Column(linkify=True)
    deployment = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = GatewayRouteTarget
        fields = ("pk", "id", "route", "deployment", "order", "weight", "created", "last_updated")
        default_columns = ("route", "deployment", "order", "weight")
