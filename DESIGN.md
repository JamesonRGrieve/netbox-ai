# netbox-ai — Design

**Status:** design / not implemented. **Captured:** 2026-06-19.

NetBox as the **single source of truth for AI/LLM deployment intent** — *which model, at which
quant, runs on which GPUs, with what parallelism/context, behind which gateway route* — consumed
by a **Semaphore-driven renderer** that materializes vLLM / SGLang / Ollama / ComfyUI launch
config and the **bifrost** gateway config. This replaces the scattered `ai-lab/` imperative
scripts (`install-*.sh`, `deploy-gigabyte-*.sh`, `modelfiles/{desktop,gigabyte,laptop}/`,
`profiles/*.sh`, `ollama_sweep.py`) with **NetBox-intent → Semaphore-apply**, the same move
`netbox-services` makes for apps and `netbox-guests` makes for guests.

`netbox-ai` is the **GPU-placement layer**. It does **not** re-model the running server or the GPU
card — it **composes**: an inference backend is a [`netbox-services`](../netbox-services/DESIGN.md)
**`ServiceInstance`**, its host is a [`netbox-guests`](../netbox-guests/DESIGN.md) guest VM or a
`dcim.Device`, and the GPU is a core `dcim` hardware record (with `netbox-inventory` as the
*optional* asset layer). `netbox-ai` adds the one thing
nothing else models: **VRAM-aware model→GPU placement with parallelism + validation.**

That composition is a **hard dependency**, not loose coupling: `InferenceDeployment` FKs
`netbox_services.ServiceInstance`, so `netbox-ai` declares
**`PluginConfig.required_plugins = ["netbox_services"]`** and won't load without it — exactly as
`netbox-load-balancing-acl` declares `required_plugins=["netbox_load_balancing"]` and FKs its
`Listener`/`Pool`. (`netbox-inventory` stays *optional* enrichment; `netbox-guests` is *transitive*
via `ServiceInstance.parent`.)

---

## 0. Decisions of record (2026-06-19)

| # | Item | Decision |
|---|------|----------|
| 1 | Scope | **GPU-placement layer only** — model catalog + GPU/VRAM allocation + placement/parallelism + gateway routing. Not a monolithic "AI plugin" that re-implements services/inventory. |
| 2 | Inference server instance | **Lives in `netbox-services` as a `ServiceInstance`** (vLLM/SGLang/Ollama/ComfyUI are apps with installs). `netbox-ai.InferenceDeployment` **FK → `ServiceInstance`** (required, not nullable — no bare-VM shortcut) and adds the model + GPU placement. *(operator decision — "it will reference ServiceInstance")* |
| 2a | Dependency posture | **`netbox-services` is a hard dependency** — `required_plugins=["netbox_services"]` (the FK makes it mandatory; netbox-ai won't load without it), the `netbox-load-balancing-acl → netbox_load_balancing` pattern. **`netbox-inventory` optional** (GpuDevice references the core-dcim GPU record; netbox-inventory adds asset/ownership only). **`netbox-guests` transitive** (via `ServiceInstance.parent`; no direct FK). |
| 3 | GPU hardware | **Core `dcim` owns the canonical GPU record** — a `Module` carrying the `gpu` module-type profile (or an `InventoryItem`). `GpuDevice` references it and **derives VRAM** from the profile (no stored copy → no drift). `netbox-inventory` is the **optional** asset/ownership layer on the same record, **not** required. *(decision 2026-06-19)* |
| 4 | Role of NetBox | **SoT + validator, not a scheduler.** NetBox stores the *chosen* plan and enforces constraints (`clean()`); the optimizer that *decides* placement is external (the `ollama_sweep.py`-style planner) and writes intent into NetBox. |
| 5 | Telemetry | **Out — monitoring, not NetBox.** NetBox holds *planned* VRAM budget + footprint estimates; live utilization / tok·s⁻¹ / actual VRAM stay in monitoring (`netbox-modeling.md §1`). |
| 6 | Model weights | **Out — object store / HF / Ollama registry.** The catalog holds a *reference* (repo / tag / size), never the blob. |
| 7 | bifrost routing | **`netbox-ai` owns `GatewayRoute`** (public model name → deployment(s) + fallbacks/limits) — AI-specific, conceptually kin to `netbox-load-balancing-acl`'s match→pool. |
| 8 | Plugin shape | **Native NetBox plugin, no core fork.** All models are `NetBoxModel`s; mirrors the `netbox-system-services` layout. Secrets (HF tokens, gateway keys) are **OpenBao path refs**, never values. |
| 9 | Sequencing | **After `netbox-guests` + `netbox-services`** (it FKs both). |
| 10 | Catalog seed | **`ModelCatalog` seeded from `ai-lab/modelfiles/*` + the sweep results**, the way `netbox-services` seeds `ServiceCatalog` from `about.json`. |
| 11 | Governance | Brings GPU serving under the **prod-netbox → prod-semaphore** mandate — starting a vLLM/Ollama by hand on a node is otherwise a banned direct apply. |

---

## 1. Why

- AI serving today is at the **pre-SoT, imperative-script stage** — exactly where app installs were
  before `netbox-services`. `ai-lab/` is a pile of `install-{vllm,sglang,ollama,speaches}.sh`,
  `deploy-gigabyte-{vllm,flux-lora}.sh`, per-host `modelfiles/{desktop,gigabyte,laptop}/`,
  `profiles/{host}.sh`, and `ollama_sweep.py` tuning runs. "What model runs where, on which GPU,
  with what TP/quant/ctx" is spread across those plus the OCR serving topology scripts
  (multi-host vLLM, PP=3). **There is no queryable, validated source of truth for placement.**
- The lab's whole trajectory is **intent in NetBox → realize via Semaphore**. GPU serving is the
  last large subsystem still hand-driven; the **no-direct-applies** mandate makes a hand-started
  inference server a policy violation. Modeling it here closes that gap.
- **SoT-boundary fit** (`netbox-modeling.md §1`) is clean: placement/config = *intent* (NetBox);
  GPU card = *inventory* (NetBox); HF/gateway tokens = OpenBao; live VRAM/throughput = monitoring;
  weights = object store. Nothing about the *deployment plan* is un-modelable.

**Gap:** nothing models the **model catalog**, **GPU/VRAM allocation**, **model→GPU placement +
parallelism**, or **gateway routing** as NetBox data. That is this plugin.

---

## 2. SoT boundary (what lives where)

| Class | Home | netbox-ai role |
|-------|------|----------------|
| Placement / config intent (model, quant, GPU set, TP/PP, ctx, gpu-mem-util, route) | **NetBox** (`netbox-ai`) | authoritative |
| Running server (vLLM/Ollama/SGLang/ComfyUI process + install) | **NetBox** (`netbox-services` `ServiceInstance`) | referenced (FK) |
| Host (guest/bare-metal) | **NetBox** (`netbox-guests` VM \| `dcim.Device`) | referenced (via ServiceInstance.parent) |
| GPU hardware (card, VRAM size, PCI) | **NetBox** (core `dcim` — `Module` + `gpu` module-type profile) | referenced; VRAM **derived** from the profile (GpuDevice → dcim) |
| GPU asset / ownership (serial, purchase, ERPNext) | **NetBox** (`netbox-inventory`, *optional*) + ERPNext | optional enrichment on the same hardware record |
| Secrets (HF tokens, gateway API keys, model EULA creds) | **OpenBao** | path/ref only |
| Telemetry (GPU util, tok·s⁻¹, live VRAM, queue depth) | **monitoring** | not stored |
| Weights / LoRAs / ComfyUI graphs | **object store / HF / registry** | reference only |

---

## 3. Data model (NetBox plugin `netbox_ai`)

All models are native `NetBoxModel`s (custom fields, tags, journaling, GraphQL for free), mirroring
the `netbox-system-services` layout. No `config_context`, no CustomField-as-data-blob.
**`PluginConfig.required_plugins = ["netbox_services"]`** — the FKs below to
`netbox_services.ServiceInstance` are required (not nullable), so the dependency is declared and
fails fast at startup (the `netbox-load-balancing-acl` pattern). The plugin migration depends on
`netbox_services`'s latest migration so the target table exists.

### ModelCatalog  *(template — the model SoT; seeded from `ai-lab/modelfiles/*`)*
`name, display_name, description, architecture` (llama / qwen3 / gemma3 / gemma4-moe / flux …),
`parameter_count` (e.g. `27B`, `26B-A4B` for MoE), `modality` (text / vision / embedding /
image-gen / audio-stt / audio-tts), `source` (hf_repo \| ollama_tag \| url — a *reference*, not the
weights), `license`, `default_context`, `max_context`, `tags`.

### ModelVariant  *(child of ModelCatalog — one row per quant; = the `family:quant-Ng` variants)*
`FK→ModelCatalog, quant` (fp16 / q8_0 / q4_K_M / awq / gptq / fp8 …), `weights_vram_gb` (declared
estimate), `recommended_context`. The thing `MODEL_TUNING.md` / the VRAM-budget tiers encode today.

### GpuDevice  *(thin serving view — references the GPU's canonical core-dcim hardware record)*
`FK→dcim.Device` (host), `index` (GPU0/GPU1 …), **`FK→dcim` GPU record** (a `Module` carrying the
`gpu` module-type profile, or an `InventoryItem`) — **`vram_total_gb` is derived from that record's
profile, not stored**; a nullable `vram_total_gb_override` covers a card not yet in dcim.
`interconnect_group` (NVLink/PCIe peer set for TP eligibility). Unique per `(device, index)`.
*Reserved* VRAM is **derived** (Σ placements), never stored. An optional `netbox-inventory` Asset
on the same record adds ownership/ERPNext — enrichment, not a dependency.

### InferenceDeployment  *(the placement — the row the renderer reads)*
`FK→netbox_services.ServiceInstance` (the running backend), `FK→ModelVariant`, `gpus` (M2M→GpuDevice),
`tensor_parallel`, `pipeline_parallel`, `gpu_memory_utilization`, `max_model_len`, `kv_cache_quant`,
`dtype`, `served_model_name`, `status` (planned/active), `estimated_vram_gb` (derived — see §4).
Backend-specific long-tail args ride a bounded typed set; an `extra_args` escape hatch is a last
resort, flagged for ratchet (don't let it become a blob).

### GatewayRoute  *(bifrost — model-name routing)*
`FK→ServiceInstance` (the bifrost gateway), `public_name` (alias clients call), `targets` (ordered
M2M→InferenceDeployment — primary + fallbacks), `weight`, `rate_limit`. Match→pool, kin to
`netbox-load-balancing-acl.LBRoutingRule`.

The integration edges (a frontend like Open WebUI/SillyTavern → the bifrost gateway → a backend) are
ordinary `netbox-services` `Integration` rows; `netbox-ai` adds only the model/GPU specifics.

---

## 4. Placement & validation (NetBox validates; an external planner decides)

NetBox is **not** the scheduler. The optimizer (a planner script, evolution of `ollama_sweep.py` /
the VRAM-budget-tier logic) computes placements and writes `InferenceDeployment` rows; NetBox
enforces the constraints in `clean()` / `pre_save`:

- **VRAM budget:** for each `GpuDevice`, `Σ estimated_vram_gb of deployments touching it ≤
  vram_total_gb × headroom`. `estimated_vram_gb ≈ weights_vram_gb / tensor_parallel + KV-cache(ctx,
  concurrency, layers) + overhead` — a declared estimate with headroom, **not** a precise predictor.
- **Tensor-parallel locality:** `tensor_parallel > 1` ⇒ all `gpus` share one host (one `dcim.Device`
  / one `interconnect_group`). **Pipeline-parallel** may span hosts (the OCR PP=3 case).
- **Served-name / port uniqueness** per host; `gpu_memory_utilization ∈ (0,1]`.

NetBox stores the *plan*; live actuals (does it actually fit, real tok·s⁻¹) are a monitoring concern,
not a NetBox field.

---

## 5. Backends

| Backend | GPU-planned (InferenceDeployment) | Notes |
|---------|-----------------------------------|-------|
| vLLM / SGLang | yes | TP/PP, gpu-mem-util, max-model-len, dtype, KV-quant |
| Ollama | yes | renders a Modelfile + `ollama create`; the `family:quant-role-Ng` variants |
| ComfyUI / Flux-LoRA | yes | image-gen; GPU + VRAM, workflow graph is an object-store reference |
| speaches (STT/TTS) | yes (lightweight) | small VRAM footprint |
| Open WebUI / SillyTavern / SearXNG / Tika | **no** | plain `netbox-services` instances; no GPU planning |
| bifrost (gateway) | no (routes, doesn't serve) | `ServiceInstance` + `GatewayRoute` rows |

---

## 6. Consumers & supersession

- **Renderer (Semaphore-driven):** reads `InferenceDeployment` + `GatewayRoute` → emits vLLM/SGLang
  launch args (systemd unit), Ollama Modelfile + `ollama create`, ComfyUI config, and the **bifrost
  `config`** (providers + model→backend map + fallbacks). Secrets (`HF_TOKEN`, gateway keys) injected
  ephemerally from OpenBao at apply. Same pattern as the `netbox-services` provider.
- **Supersedes** `ai-lab/install-*.sh`, `deploy-gigabyte-*.sh`, `modelfiles/*`, `profiles/*` — those
  become a generated projection of NetBox (the `about.json`-is-generated pattern), or are retired.
- **Seeder:** `ai-lab/modelfiles/*` + sweep results → `ModelCatalog` / `ModelVariant` (idempotent,
  the `netbox-services` `about.json` seeder pattern).

---

## 7. Build sequence

1. `netbox-guests` (guest VMs) + `netbox-services` (`ServiceInstance`) land first — `netbox-ai` FKs both.
2. `netbox-inventory` GPU records exist for the served hosts (desktop 3090/970, gigabyte, CT hosts).
3. `netbox_ai` plugin: `ModelCatalog`/`ModelVariant`, `GpuDevice`, `InferenceDeployment`, `GatewayRoute`
   + REST/GraphQL/UI/tests (mirror `netbox-system-services`); validation in `clean()`/`pre_save`.
4. Catalog seeder from `ai-lab/modelfiles`.
5. The Semaphore renderer (vLLM/Ollama/ComfyUI/bifrost) + import-first adoption of the live serving
   topology to 0-diff.

---

## 8. Open questions / risks

- **Overlap with `netbox-services`** is the #1 risk — `netbox-ai` must stay the GPU-placement layer
  *on top of* `ServiceInstance`, never a parallel instance/integration model.
- **VRAM estimation** is approximate (KV cache scales with ctx × concurrency × layers) — model it as a
  declared estimate + headroom, validated against GPU total; don't oversell precision.
- **Cross-host PP** needs an interconnect/latency notion — start single-host TP, add cross-host PP once
  the single-host case is 0-diff.
- **`extra_args` escape hatch** — bound it; ratchet long-tail backend args into typed fields, don't let
  it regress to a blob.
- **GpuDevice VRAM derivation** — resolved (2026-06-19): VRAM is derived from the core-dcim `gpu`
  module-type profile; `GpuDevice` holds only the serving `index` + `interconnect_group` (+ a nullable
  `vram_total_gb_override` for a card not yet in dcim). Verify the running NetBox's `gpu` profile schema
  actually carries a VRAM attribute.

---

## 9. References

- `ai-lab/` — `install-*.sh`, `deploy-gigabyte-*.sh`, `modelfiles/{desktop,gigabyte,laptop}/`,
  `profiles/*.sh`, `scripts/ollama_sweep.py`, `MODEL_TUNING.md` (the imperative SoT this supersedes).
- Sibling plugins: [`netbox-services`](../netbox-services/DESIGN.md) (`ServiceInstance` — the FK target),
  [`netbox-guests`](../netbox-guests/DESIGN.md) (guest hosts), `netbox-load-balancing-acl` (routing kin),
  structural reference `netbox-system-services` (layout).
- `prod-lab/docs/netbox-modeling.md` (SoT boundary; `netbox-inventory` gpu profile), `netbox-tofu-bao.md`
  (NetBox→Semaphore→OpenBao wiring).
