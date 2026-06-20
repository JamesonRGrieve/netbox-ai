# SPDX-License-Identifier: AGPL-3.0-or-later
"""The netbox-ai data model: a model **catalog** (``ModelCatalog`` + ``ModelVariant``), a thin
serving **view** of a GPU card (``GpuDevice`` — references the core-dcim hardware record and
*derives* VRAM), the **placement** (``InferenceDeployment`` — model→GPU with parallelism, FKs the
``netbox_services.ServiceInstance`` backend), and **gateway routing** (``GatewayRoute`` +
``GatewayRouteTarget``). NetBox validates placement; an external planner decides it (DESIGN §4).

Derive-don't-store discipline: ``GpuDevice.vram_total_gb`` comes from the dcim profile, reserved
VRAM is Σ placements, and ``InferenceDeployment.estimated_vram_gb`` is computed — no stored copies,
no drift.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from netbox.plugins import get_plugin_config

from .choices import (
    DeploymentStatusChoices,
    DTypeChoices,
    KVCacheQuantChoices,
    ModalityChoices,
    ModelSourceTypeChoices,
    QuantizationChoices,
)

# GpuDevice.gpu_hardware GFK is limited to the canonical core-dcim GPU record: a Module carrying the
# `gpu` module-type profile, or an InventoryItem. (netbox-inventory's Asset rides the same record as
# optional enrichment; it is not referenced here.)
GPU_HARDWARE_CT_LIMIT = models.Q(
    models.Q(("app_label", "dcim"), ("model", "module")),
    models.Q(("app_label", "dcim"), ("model", "inventoryitem")),
    _connector="OR",
)


def _as_float(value):
    """Best-effort coerce a derived attribute (profile/custom-field value) to ``float`` or ``None``."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ModelCatalog(NetBoxModel):
    """A servable model *family* — the model SoT, seeded from ``ai-lab/modelfiles/*`` + sweep results.
    Holds a *reference* to the weights (``source_type`` + ``source``), never the blob."""

    name = models.SlugField(max_length=120, unique=True, help_text="Stable catalog key (e.g. qwen3-coder-30b).")
    display_name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    architecture = models.CharField(
        max_length=64, blank=True, help_text="Model architecture, e.g. llama / qwen3 / gemma3 / flux."
    )
    parameter_count = models.CharField(
        max_length=32, blank=True, help_text="Parameter count label, e.g. 27B or 26B-A4B (MoE)."
    )
    modality = models.CharField(max_length=16, choices=ModalityChoices, default=ModalityChoices.TEXT)
    source_type = models.CharField(max_length=16, choices=ModelSourceTypeChoices, default=ModelSourceTypeChoices.HF_REPO)
    source = models.CharField(max_length=255, help_text="Weights reference (HF repo / ollama tag / URL) — not the blob.")
    license = models.CharField(max_length=100, blank=True)
    default_context = models.PositiveIntegerField(null=True, blank=True, help_text="Default context window (tokens).")
    max_context = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum supported context (tokens).")

    class Meta:
        ordering = ["name"]
        verbose_name = "Model Catalog"
        verbose_name_plural = "Model Catalog"

    def __str__(self):
        return self.display_name or self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:modelcatalog", args=[self.pk])

    def get_modality_color(self):
        return ModalityChoices.colors.get(self.modality)


class ModelVariant(NetBoxModel):
    """One quantization of a :class:`ModelCatalog` (the ``family:quant`` row). ``weights_vram_gb`` is
    the declared weight footprint the VRAM-budget estimate builds on (DESIGN §4)."""

    model = models.ForeignKey(ModelCatalog, on_delete=models.CASCADE, related_name="variants")
    quant = models.CharField(max_length=16, choices=QuantizationChoices)
    weights_vram_gb = models.FloatField(
        null=True, blank=True, help_text="Declared weight VRAM footprint at this quant, in GiB."
    )
    recommended_context = models.PositiveIntegerField(
        null=True, blank=True, help_text="Recommended max_model_len for this variant (tokens)."
    )

    class Meta:
        ordering = ["model", "quant"]
        verbose_name = "Model Variant"
        constraints = [
            models.UniqueConstraint(fields=["model", "quant"], name="netbox_ai_modelvariant_unique")
        ]

    def __str__(self):
        return f"{self.model.name}:{self.quant}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:modelvariant", args=[self.pk])

    def get_quant_color(self):
        return QuantizationChoices.colors.get(self.quant)


class GpuDevice(NetBoxModel):
    """A serving view of one GPU on a host. References the canonical core-dcim hardware record and
    **derives** total VRAM from its ``gpu`` module-type profile — no stored copy. A nullable
    ``vram_total_gb_override`` covers a card not yet in dcim. Reserved VRAM is Σ placements (derived)."""

    device = models.ForeignKey(
        "dcim.Device", on_delete=models.CASCADE, related_name="gpu_devices", help_text="The host the GPU is in."
    )
    index = models.PositiveSmallIntegerField(help_text="GPU ordinal on the host (GPU0, GPU1, …).")
    gpu_hardware_object_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.PROTECT, related_name="+", null=True, blank=True,
        limit_choices_to=GPU_HARDWARE_CT_LIMIT,
    )
    gpu_hardware_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    gpu_hardware = GenericForeignKey("gpu_hardware_object_type", "gpu_hardware_object_id")
    vram_total_gb_override = models.FloatField(
        null=True, blank=True, help_text="Override total VRAM (GiB) when the card is not yet a dcim record."
    )
    interconnect_group = models.CharField(
        max_length=64, blank=True, help_text="NVLink/PCIe peer-set label; GPUs in one group are TP-eligible together."
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["device", "index"]
        verbose_name = "GPU Device"
        constraints = [
            models.UniqueConstraint(fields=["device", "index"], name="netbox_ai_gpudevice_unique_device_index")
        ]
        indexes = [models.Index(fields=["gpu_hardware_object_type", "gpu_hardware_object_id"], name="netbox_ai_gpu_hw_idx")]

    def __str__(self):
        return f"{self.device} GPU{self.index}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:gpudevice", args=[self.pk])

    @property
    def vram_total_gb(self):
        """Total VRAM (GiB): the override if set, else derived from the dcim GPU record's profile /
        custom-field attribute (``gpu_vram_attribute`` plugin setting), else ``None`` (unknown)."""
        if self.vram_total_gb_override is not None:
            return self.vram_total_gb_override
        hardware = self.gpu_hardware
        if hardware is None:
            return None
        attribute = get_plugin_config("netbox_ai", "gpu_vram_attribute")
        module_type = getattr(hardware, "module_type", None)
        if module_type is not None:
            for source in (getattr(module_type, "attribute_data", None), getattr(module_type, "custom_field_data", None)):
                if source and attribute in source:
                    return _as_float(source[attribute])
        own_cf = getattr(hardware, "custom_field_data", None)
        if own_cf and attribute in own_cf:
            return _as_float(own_cf[attribute])
        return None

    @property
    def reserved_vram_gb(self):
        """Σ of the per-GPU VRAM estimate of every deployment touching this GPU (derived, not stored)."""
        return round(sum(d.estimated_vram_gb for d in self.deployments.all()), 2)


class InferenceDeployment(NetBoxModel):
    """The placement the renderer reads: a :class:`ModelVariant` served by a
    :class:`netbox_services.ServiceInstance` backend across one or more :class:`GpuDevice`s, with
    tensor/pipeline parallelism. ``estimated_vram_gb`` is the derived per-GPU footprint (DESIGN §4)."""

    service_instance = models.ForeignKey(
        "netbox_services.ServiceInstance", on_delete=models.PROTECT, related_name="ai_deployments",
        help_text="The running inference backend (vLLM/SGLang/Ollama/ComfyUI) this placement runs on.",
    )
    variant = models.ForeignKey(ModelVariant, on_delete=models.PROTECT, related_name="deployments")
    gpus = models.ManyToManyField(GpuDevice, related_name="deployments", blank=True)
    tensor_parallel = models.PositiveSmallIntegerField(default=1, help_text="Tensor-parallel degree (TP).")
    pipeline_parallel = models.PositiveSmallIntegerField(
        default=1, help_text="Pipeline-parallel degree (PP); may span hosts."
    )
    gpu_memory_utilization = models.FloatField(
        default=0.9, help_text="Fraction of each GPU's VRAM the backend may use (vLLM --gpu-memory-utilization)."
    )
    max_model_len = models.PositiveIntegerField(null=True, blank=True, help_text="Served context length (tokens).")
    kv_cache_quant = models.CharField(max_length=16, choices=KVCacheQuantChoices, blank=True)
    dtype = models.CharField(max_length=16, choices=DTypeChoices, default=DTypeChoices.AUTO)
    served_model_name = models.CharField(max_length=200, help_text="Name the backend serves the model under.")
    status = models.CharField(max_length=16, choices=DeploymentStatusChoices, default=DeploymentStatusChoices.PLANNED)
    extra_args = ArrayField(
        models.CharField(max_length=200), default=list, blank=True,
        help_text="Bounded escape hatch for backend args not yet a typed field (DESIGN §8 — ratchet to zero).",
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["service_instance", "served_model_name"]
        verbose_name = "Inference Deployment"

    def __str__(self):
        return f"{self.served_model_name} ({self.variant})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:inferencedeployment", args=[self.pk])

    def get_status_color(self):
        return DeploymentStatusChoices.colors.get(self.status)

    @property
    def shard_count(self):
        """Number of GPU shards the weights split across (TP × PP)."""
        return max(self.tensor_parallel * self.pipeline_parallel, 1)

    @property
    def kv_cache_gb(self):
        """Declared KV-cache VRAM estimate across all shards (GiB). Scales with ``max_model_len``;
        approximate (KV also scales with concurrency × layers) — a budget input, not a predictor."""
        if not self.max_model_len:
            return 0.0
        coefficient = get_plugin_config("netbox_ai", "kv_cache_gb_per_1k_tokens")
        return (self.max_model_len / 1000.0) * coefficient

    @property
    def estimated_vram_total_gb(self):
        """Whole-deployment VRAM estimate (GiB) = weights + KV-cache + per-shard overhead."""
        weights = (self.variant.weights_vram_gb or 0.0) if self.variant_id else 0.0
        overhead = get_plugin_config("netbox_ai", "vram_overhead_gb") * self.shard_count
        return round(weights + self.kv_cache_gb + overhead, 2)

    @property
    def estimated_vram_gb(self):
        """Per-GPU VRAM estimate (GiB) — the figure summed against each GPU's budget (DESIGN §4)."""
        return round(self.estimated_vram_total_gb / self.shard_count, 2)

    def clean(self):
        super().clean()
        if not (0.0 < self.gpu_memory_utilization <= 1.0):
            raise ValidationError({"gpu_memory_utilization": "Must be in (0, 1]."})
        if self.tensor_parallel < 1:
            raise ValidationError({"tensor_parallel": "Must be at least 1."})
        if self.pipeline_parallel < 1:
            raise ValidationError({"pipeline_parallel": "Must be at least 1."})
        if self.service_instance_id and self.served_model_name:
            host_ct = self.service_instance.parent_object_type_id
            host_id = self.service_instance.parent_object_id
            clash = InferenceDeployment.objects.filter(
                served_model_name=self.served_model_name,
                service_instance__parent_object_type_id=host_ct,
                service_instance__parent_object_id=host_id,
            ).exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError(
                    {"served_model_name": f"'{self.served_model_name}' is already served on this host."}
                )


def validate_deployment_placement(deployment, gpus):
    """GPU-set validation for an :class:`InferenceDeployment` (DESIGN §4). Called from the form
    ``clean()`` (with the submitted GPUs) and the ``m2m_changed`` backstop (with the saved set), so
    the ORM/seeder/planner path is covered too. ``gpus`` is an iterable of :class:`GpuDevice`."""
    gpus = list(gpus)
    if not gpus:
        return

    expected = deployment.tensor_parallel * deployment.pipeline_parallel
    if len(gpus) != expected:
        raise ValidationError(
            f"{len(gpus)} GPU(s) assigned but tensor_parallel × pipeline_parallel = {expected}."
        )

    if deployment.tensor_parallel > 1:
        if len({g.device_id for g in gpus}) > 1:
            raise ValidationError("tensor_parallel > 1 requires all GPUs on a single host (one dcim.Device).")
        groups = {g.interconnect_group for g in gpus if g.interconnect_group}
        if len(groups) > 1:
            raise ValidationError("tensor_parallel GPUs must share one interconnect_group.")

    headroom = get_plugin_config("netbox_ai", "vram_headroom")
    per_gpu = deployment.estimated_vram_gb
    for gpu in gpus:
        total = gpu.vram_total_gb
        if total is None:
            continue  # unknown total (no dcim record, no override) — budget unenforceable, skip
        others = gpu.deployments.exclude(pk=deployment.pk) if deployment.pk else gpu.deployments.all()
        used = sum(d.estimated_vram_gb for d in others)
        if used + per_gpu > total * headroom:
            raise ValidationError(
                f"{gpu} VRAM budget exceeded: {used + per_gpu:.1f} GiB needed > "
                f"{total * headroom:.1f} GiB available ({total} GiB × {headroom} headroom)."
            )


class GatewayRoute(NetBoxModel):
    """A bifrost public model-name route: ``public_name`` → ordered :class:`InferenceDeployment`
    targets (primary + fallbacks, via :class:`GatewayRouteTarget`). Match→pool, kin to
    ``netbox-load-balancing-acl.LBRoutingRule`` (DESIGN §3)."""

    service_instance = models.ForeignKey(
        "netbox_services.ServiceInstance", on_delete=models.PROTECT, related_name="gateway_routes",
        help_text="The bifrost gateway ServiceInstance this route lives on.",
    )
    public_name = models.CharField(max_length=200, help_text="Public model name clients call (the alias).")
    targets = models.ManyToManyField(
        InferenceDeployment, through="GatewayRouteTarget", related_name="gateway_routes", blank=True
    )
    rate_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Requests per minute (None = unlimited).")
    status = models.CharField(max_length=16, choices=DeploymentStatusChoices, default=DeploymentStatusChoices.PLANNED)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["service_instance", "public_name"]
        verbose_name = "Gateway Route"
        constraints = [
            models.UniqueConstraint(
                fields=["service_instance", "public_name"], name="netbox_ai_gatewayroute_unique_name"
            )
        ]

    def __str__(self):
        return self.public_name

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:gatewayroute", args=[self.pk])

    def get_status_color(self):
        return DeploymentStatusChoices.colors.get(self.status)


class GatewayRouteTarget(NetBoxModel):
    """One ordered, weighted target of a :class:`GatewayRoute` (the through row). Lowest ``order`` is
    the primary; higher orders are fallbacks; ``weight`` splits traffic among equal-order targets."""

    route = models.ForeignKey(GatewayRoute, on_delete=models.CASCADE, related_name="route_targets")
    deployment = models.ForeignKey(InferenceDeployment, on_delete=models.PROTECT, related_name="route_targets")
    order = models.PositiveIntegerField(default=100, help_text="Selection order; lower is preferred (primary).")
    weight = models.PositiveSmallIntegerField(default=1, help_text="Relative weight among equal-order targets.")

    class Meta:
        ordering = ["route", "order", "pk"]
        verbose_name = "Gateway Route Target"
        constraints = [
            models.UniqueConstraint(fields=["route", "deployment"], name="netbox_ai_gatewayroutetarget_unique")
        ]

    def __str__(self):
        return f"{self.route.public_name} → {self.deployment.served_model_name} (#{self.order})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_ai:gatewayroutetarget", args=[self.pk])
