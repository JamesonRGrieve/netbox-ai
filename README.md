# netbox-ai

NetBox-native modeling of **AI/LLM deployment intent** — which model, at which quant, runs on which
GPUs, with what parallelism/context, behind which gateway route — the source of truth a
Semaphore-driven renderer reads to deploy **vLLM / SGLang / Ollama / ComfyUI** and configure the
**bifrost** gateway. Supersedes the imperative `ai-lab/` scripts the way `netbox-services` supersedes
`about.json`.

`netbox-ai` is the **GPU-placement layer** — it **composes**, it doesn't re-model:

- the running inference server is a [`netbox-services`](../netbox-services) **`ServiceInstance`**
  (`InferenceDeployment` FKs it);
- the host is a [`netbox-guests`](../netbox-guests) guest VM or a `dcim.Device`;
- the GPU card is a core `dcim` hardware record — `GpuDevice` references it and **derives VRAM**
  from the `gpu` module-type profile (`netbox-inventory` is optional, for asset/ownership only).

It adds the one thing nothing else models: **VRAM-aware model→GPU placement with tensor/pipeline
parallelism + validation** (NetBox is the SoT + validator; an external planner decides placement).

**Secret policy:** HF tokens and gateway API keys are OpenBao path references, never stored. Live
GPU telemetry is monitoring's job, not NetBox's; model weights live in the registry/object store.

**Status:** implemented (NetBox 4.6 plugin, `netbox_ai`). Models — `ModelCatalog` / `ModelVariant`
(model SoT), `GpuDevice` (derives VRAM from the core-dcim `gpu` profile), `InferenceDeployment`
(VRAM-aware model→GPU placement with TP/PP + validation), `GatewayRoute` / `GatewayRouteTarget`
(bifrost routing). Full REST + UI + filtersets + tests, mirroring the sibling
[`netbox-services`](../netbox-services). Requires `netbox-services` (declared
`required_plugins`). See **[DESIGN.md](DESIGN.md)** for the decision record and the SoT boundary, and
**[CLAUDE.md](CLAUDE.md)** for the agent operating guide + verification still owed on a live NetBox.

### Install

```bash
pip install -e .            # pulls netbox-services
# enable in netbox configuration.py:  PLUGINS = ["netbox_services", "netbox_ai"]
python manage.py migrate netbox_ai
```

Optional `PLUGINS_CONFIG["netbox_ai"]` settings (defaults shown): `vram_headroom` (`0.9`),
`kv_cache_gb_per_1k_tokens` (`0.5`), `vram_overhead_gb` (`1.0`), `gpu_vram_attribute` (`"vram_gb"` —
set to the live netbox-inventory `gpu` profile's VRAM attribute name).
