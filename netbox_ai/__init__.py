# SPDX-License-Identifier: AGPL-3.0-or-later
"""netbox-ai: NetBox as the source of truth for **AI/LLM deployment intent** — which model, at
which quant, runs on which GPUs, with what parallelism/context, behind which gateway route — the
data a Semaphore-driven renderer reads to deploy vLLM / SGLang / Ollama / ComfyUI and configure the
**bifrost** gateway.

netbox-ai is the **GPU-placement layer**; it composes rather than re-models. The running inference
backend is a :class:`netbox_services.ServiceInstance` (``InferenceDeployment`` FKs it — a hard
dependency, so ``required_plugins`` lists ``netbox_services``); the GPU card is a core ``dcim``
hardware record (``GpuDevice`` references it and **derives** VRAM from the ``gpu`` module-type
profile — netbox-inventory is optional asset enrichment, not a dependency). The one thing nothing
else models lives here: **VRAM-aware model→GPU placement with tensor/pipeline parallelism +
validation** (NetBox is the SoT + validator; an external planner decides placement).

**Secret policy:** HF tokens and gateway API keys are OpenBao path references handled by
``netbox-services``; secret values never live here. Live GPU telemetry is monitoring's job; model
weights are an object-store / registry *reference*, never a stored blob.
"""
from netbox.plugins import PluginConfig

__version__ = "0.0.1"


class NetBoxAIConfig(PluginConfig):
    name = "netbox_ai"
    verbose_name = "NetBox AI"
    description = "Native SoT for AI/LLM deployment intent — model catalog + VRAM-aware GPU placement + gateway routing"
    version = __version__
    author = "Jameson"
    base_url = "ai"
    min_version = "4.6.0"
    max_version = "4.6.99"
    # InferenceDeployment FKs netbox_services.ServiceInstance (required, not nullable), so the
    # dependency is hard and fails fast at startup — the netbox-load-balancing-acl pattern.
    required_plugins = ["netbox_services"]
    default_settings = {
        # Budget = GpuDevice.vram_total_gb × headroom (leaves room for fragmentation/runtime growth).
        "vram_headroom": 0.9,
        # KV-cache VRAM estimate coefficient: GiB consumed per 1k tokens of max_model_len. A declared
        # estimate (KV scales with ctx × concurrency × layers); not a precise predictor (DESIGN §4).
        "kv_cache_gb_per_1k_tokens": 0.5,
        # Per-GPU framework/activation overhead added to every deployment shard, in GiB.
        "vram_overhead_gb": 1.0,
        # The gpu module-type-profile / custom-field attribute GpuDevice derives total VRAM from.
        # Re-confirm against the live netbox-inventory `gpu` profile schema (DESIGN §8).
        "gpu_vram_attribute": "vram_gb",
    }

    def ready(self):
        super().ready()
        from . import signals  # noqa: F401  (wires the placement-validation ORM backstops)


config = NetBoxAIConfig
