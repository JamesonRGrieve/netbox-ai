# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored initial migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_ai --check --dry-run   (on a dev/ephemeral NetBox)
# Re-confirm against the pinned NetBox 4.6: the GpuDevice.gpu_hardware GFK (object_type/_id) +
# limit_choices_to Q serialization, the netbox_services.ServiceInstance FK target, and the
# GatewayRoute.targets through-M2M (split CreateModel + AddField to break the route↔target cycle).
import django.contrib.postgres.fields
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models

_BASE = [
    ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
    ("created", models.DateTimeField(auto_now_add=True, blank=True, null=True)),
    ("last_updated", models.DateTimeField(auto_now=True, blank=True, null=True)),
    ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
]
_TAGS = ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag"))

# GpuDevice.gpu_hardware GFK is limited to the canonical core-dcim GPU record (Module | InventoryItem).
_GPU_HW_CT_LIMIT = models.Q(
    models.Q(("app_label", "dcim"), ("model", "module")),
    models.Q(("app_label", "dcim"), ("model", "inventoryitem")),
    _connector="OR",
)


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("contenttypes", "0001_initial"),
        # NetBox 4.6 squashes core app migrations; pin to __first__ rather than a nonexistent 0001_initial.
        ("dcim", "__first__"),
        ("extras", "__first__"),
        # InferenceDeployment/GatewayRoute FK netbox_services.ServiceInstance — its table must exist.
        ("netbox_services", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="ModelCatalog",
            fields=[
                *_BASE,
                ("name", models.SlugField(max_length=120, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("architecture", models.CharField(blank=True, max_length=64)),
                ("parameter_count", models.CharField(blank=True, max_length=32)),
                ("modality", models.CharField(default="text", max_length=16)),
                ("source_type", models.CharField(default="hf_repo", max_length=16)),
                ("source", models.CharField(max_length=255)),
                ("license", models.CharField(blank=True, max_length=100)),
                ("default_context", models.PositiveIntegerField(blank=True, null=True)),
                ("max_context", models.PositiveIntegerField(blank=True, null=True)),
                _TAGS,
            ],
            options={"verbose_name": "Model Catalog", "verbose_name_plural": "Model Catalog", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ModelVariant",
            fields=[
                *_BASE,
                ("quant", models.CharField(max_length=16)),
                ("weights_vram_gb", models.FloatField(blank=True, null=True)),
                ("recommended_context", models.PositiveIntegerField(blank=True, null=True)),
                ("model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="netbox_ai.modelcatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Model Variant",
                "ordering": ["model", "quant"],
                "constraints": [models.UniqueConstraint(fields=("model", "quant"), name="netbox_ai_modelvariant_unique")],
            },
        ),
        migrations.CreateModel(
            name="GpuDevice",
            fields=[
                *_BASE,
                ("index", models.PositiveSmallIntegerField()),
                ("gpu_hardware_object_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("vram_total_gb_override", models.FloatField(blank=True, null=True)),
                ("interconnect_group", models.CharField(blank=True, max_length=64)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gpu_devices", to="dcim.device")),
                ("gpu_hardware_object_type", models.ForeignKey(blank=True, limit_choices_to=_GPU_HW_CT_LIMIT, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="contenttypes.contenttype")),
                _TAGS,
            ],
            options={
                "verbose_name": "GPU Device",
                "ordering": ["device", "index"],
                "constraints": [models.UniqueConstraint(fields=("device", "index"), name="netbox_ai_gpudevice_unique_device_index")],
                "indexes": [models.Index(fields=["gpu_hardware_object_type", "gpu_hardware_object_id"], name="netbox_ai_gpu_hw_idx")],
            },
        ),
        migrations.CreateModel(
            name="InferenceDeployment",
            fields=[
                *_BASE,
                ("tensor_parallel", models.PositiveSmallIntegerField(default=1)),
                ("pipeline_parallel", models.PositiveSmallIntegerField(default=1)),
                ("gpu_memory_utilization", models.FloatField(default=0.9)),
                ("max_model_len", models.PositiveIntegerField(blank=True, null=True)),
                ("kv_cache_quant", models.CharField(blank=True, max_length=16)),
                ("dtype", models.CharField(default="auto", max_length=16)),
                ("served_model_name", models.CharField(max_length=200)),
                ("status", models.CharField(default="planned", max_length=16)),
                ("extra_args", django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, size=None)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("service_instance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ai_deployments", to="netbox_services.serviceinstance")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deployments", to="netbox_ai.modelvariant")),
                ("gpus", models.ManyToManyField(blank=True, related_name="deployments", to="netbox_ai.gpudevice")),
                _TAGS,
            ],
            options={
                "verbose_name": "Inference Deployment",
                "ordering": ["service_instance", "served_model_name"],
            },
        ),
        migrations.CreateModel(
            name="GatewayRoute",
            fields=[
                *_BASE,
                ("public_name", models.CharField(max_length=200)),
                ("rate_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("status", models.CharField(default="planned", max_length=16)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("service_instance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gateway_routes", to="netbox_services.serviceinstance")),
                _TAGS,
            ],
            options={
                "verbose_name": "Gateway Route",
                "ordering": ["service_instance", "public_name"],
                "constraints": [models.UniqueConstraint(fields=("service_instance", "public_name"), name="netbox_ai_gatewayroute_unique_name")],
            },
        ),
        migrations.CreateModel(
            name="GatewayRouteTarget",
            fields=[
                *_BASE,
                ("order", models.PositiveIntegerField(default=100)),
                ("weight", models.PositiveSmallIntegerField(default=1)),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="route_targets", to="netbox_ai.gatewayroute")),
                ("deployment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="route_targets", to="netbox_ai.inferencedeployment")),
                _TAGS,
            ],
            options={
                "verbose_name": "Gateway Route Target",
                "ordering": ["route", "order", "pk"],
                "constraints": [models.UniqueConstraint(fields=("route", "deployment"), name="netbox_ai_gatewayroutetarget_unique")],
            },
        ),
        migrations.AddField(
            model_name="gatewayroute",
            name="targets",
            field=models.ManyToManyField(blank=True, related_name="gateway_routes", through="netbox_ai.GatewayRouteTarget", to="netbox_ai.inferencedeployment"),
        ),
    ]
