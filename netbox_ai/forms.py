# SPDX-License-Identifier: AGPL-3.0-or-later
"""UI forms. The GPU hardware GFK is surfaced as two optional fields (a dcim Module or an
InventoryItem) reconciled in ``clean()``; placement validation runs in
``InferenceDeploymentForm.clean`` against the submitted GPU set (the ORM path is covered by the
``m2m_changed`` signal backstop)."""
from dcim.models import Device, InventoryItem, Module
from django import forms
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from netbox_services.models import ServiceInstance
from utilities.forms.fields import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

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
    validate_deployment_placement,
)


class ModelCatalogForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("name", "display_name", "description", name="Identity"),
        FieldSet("architecture", "parameter_count", "modality", name="Architecture"),
        FieldSet("source_type", "source", "license", name="Source"),
        FieldSet("default_context", "max_context", name="Context"),
    )

    class Meta:
        model = ModelCatalog
        fields = ["name", "display_name", "description", "architecture", "parameter_count", "modality",
                  "source_type", "source", "license", "default_context", "max_context", "tags"]


class ModelVariantForm(NetBoxModelForm):
    model = DynamicModelChoiceField(queryset=ModelCatalog.objects.all(), label="Model")

    class Meta:
        model = ModelVariant
        fields = ["model", "quant", "weights_vram_gb", "recommended_context", "tags"]


class GpuDeviceForm(NetBoxModelForm):
    device = DynamicModelChoiceField(queryset=Device.objects.all(), label="Host")
    module = DynamicModelChoiceField(queryset=Module.objects.all(), required=False, label="dcim Module")
    inventory_item = DynamicModelChoiceField(
        queryset=InventoryItem.objects.all(), required=False, label="dcim Inventory item"
    )

    fieldsets = (
        FieldSet("device", "index", "interconnect_group", "description", name="GPU"),
        FieldSet("module", "inventory_item", "vram_total_gb_override", name="Hardware record (set at most one)"),
    )

    class Meta:
        model = GpuDevice
        fields = ["device", "index", "interconnect_group", "vram_total_gb_override", "description", "tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hardware = getattr(self.instance, "gpu_hardware", None)
        if isinstance(hardware, Module):
            self.fields["module"].initial = hardware.pk
        elif isinstance(hardware, InventoryItem):
            self.fields["inventory_item"].initial = hardware.pk

    def clean(self):
        super().clean()
        module = self.cleaned_data.get("module")
        inventory_item = self.cleaned_data.get("inventory_item")
        if module and inventory_item:
            raise forms.ValidationError("Set at most one hardware record: a Module or an Inventory item, not both.")
        self.instance.gpu_hardware = module or inventory_item
        return self.cleaned_data


class InferenceDeploymentForm(NetBoxModelForm):
    service_instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all(), label="Backend (ServiceInstance)")
    variant = DynamicModelChoiceField(queryset=ModelVariant.objects.all())
    gpus = DynamicModelMultipleChoiceField(queryset=GpuDevice.objects.all(), required=False)

    fieldsets = (
        FieldSet("served_model_name", "service_instance", "variant", "status", name="Placement"),
        FieldSet("gpus", "tensor_parallel", "pipeline_parallel", name="GPUs & parallelism"),
        FieldSet("gpu_memory_utilization", "max_model_len", "kv_cache_quant", "dtype", "extra_args", name="Runtime"),
    )

    class Meta:
        model = InferenceDeployment
        fields = ["served_model_name", "service_instance", "variant", "status", "gpus", "tensor_parallel",
                  "pipeline_parallel", "gpu_memory_utilization", "max_model_len", "kv_cache_quant", "dtype",
                  "extra_args", "description", "tags"]

    def clean(self):
        super().clean()
        gpus = self.cleaned_data.get("gpus")
        if gpus is not None:
            validate_deployment_placement(self.instance, gpus)
        return self.cleaned_data


class GatewayRouteForm(NetBoxModelForm):
    service_instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all(), label="Gateway (ServiceInstance)")

    fieldsets = (
        FieldSet("public_name", "service_instance", "status", "rate_limit", "description", name="Route"),
    )

    class Meta:
        model = GatewayRoute
        fields = ["public_name", "service_instance", "status", "rate_limit", "description", "tags"]


class GatewayRouteTargetForm(NetBoxModelForm):
    route = DynamicModelChoiceField(queryset=GatewayRoute.objects.all())
    deployment = DynamicModelChoiceField(queryset=InferenceDeployment.objects.all())

    class Meta:
        model = GatewayRouteTarget
        fields = ["route", "deployment", "order", "weight", "tags"]


# --- Filter forms -----------------------------------------------------------------------------


class ModelCatalogFilterForm(NetBoxModelFilterSetForm):
    model = ModelCatalog
    modality = forms.MultipleChoiceField(choices=ModalityChoices, required=False)
    source_type = forms.MultipleChoiceField(choices=ModelSourceTypeChoices, required=False)
    architecture = forms.CharField(required=False)
    tag = TagFilterField(ModelCatalog)


class ModelVariantFilterForm(NetBoxModelFilterSetForm):
    model = ModelVariant
    model_id = DynamicModelMultipleChoiceField(queryset=ModelCatalog.objects.all(), required=False, label="Model")
    quant = forms.MultipleChoiceField(choices=QuantizationChoices, required=False)
    tag = TagFilterField(ModelVariant)


class GpuDeviceFilterForm(NetBoxModelFilterSetForm):
    model = GpuDevice
    device_id = DynamicModelMultipleChoiceField(queryset=Device.objects.all(), required=False, label="Host")
    interconnect_group = forms.CharField(required=False)
    tag = TagFilterField(GpuDevice)


class InferenceDeploymentFilterForm(NetBoxModelFilterSetForm):
    model = InferenceDeployment
    service_instance_id = DynamicModelMultipleChoiceField(
        queryset=ServiceInstance.objects.all(), required=False, label="Backend"
    )
    variant_id = DynamicModelMultipleChoiceField(queryset=ModelVariant.objects.all(), required=False, label="Variant")
    status = forms.MultipleChoiceField(choices=DeploymentStatusChoices, required=False)
    dtype = forms.MultipleChoiceField(choices=DTypeChoices, required=False)
    kv_cache_quant = forms.MultipleChoiceField(choices=KVCacheQuantChoices, required=False)
    tag = TagFilterField(InferenceDeployment)


class GatewayRouteFilterForm(NetBoxModelFilterSetForm):
    model = GatewayRoute
    service_instance_id = DynamicModelMultipleChoiceField(
        queryset=ServiceInstance.objects.all(), required=False, label="Gateway"
    )
    status = forms.MultipleChoiceField(choices=DeploymentStatusChoices, required=False)
    tag = TagFilterField(GatewayRoute)


class GatewayRouteTargetFilterForm(NetBoxModelFilterSetForm):
    model = GatewayRouteTarget
    route_id = DynamicModelMultipleChoiceField(queryset=GatewayRoute.objects.all(), required=False, label="Route")
    deployment_id = DynamicModelMultipleChoiceField(
        queryset=InferenceDeployment.objects.all(), required=False, label="Deployment"
    )
    tag = TagFilterField(GatewayRouteTarget)
