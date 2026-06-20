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
- the GPU card is a `netbox-inventory` asset (a thin `GpuDevice` references it).

It adds the one thing nothing else models: **VRAM-aware model→GPU placement with tensor/pipeline
parallelism + validation** (NetBox is the SoT + validator; an external planner decides placement).

**Secret policy:** HF tokens and gateway API keys are OpenBao path references, never stored. Live
GPU telemetry is monitoring's job, not NetBox's; model weights live in the registry/object store.

**Status:** design only. See **[DESIGN.md](DESIGN.md)** — data model (`ModelCatalog`/`ModelVariant`,
`GpuDevice`, `InferenceDeployment`, `GatewayRoute`), the SoT boundary, placement/validation rules, and
build sequence. Pairs with the sibling [`netbox-services`](../netbox-services) and
[`netbox-guests`](../netbox-guests).
