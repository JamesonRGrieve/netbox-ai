# netbox-ai — Agent Operating Guide

Adapted from the sibling `../netbox-services` / `../netbox-guests` plugins (same engineering + test
discipline), re-targeted to the **AI/LLM GPU-placement layer**.

`netbox-ai` is an **AGPL-3.0** NetBox 4.6 plugin: the **native source of truth for AI/LLM deployment
intent** — which model, at which quant, runs on which GPUs, with what parallelism/context, behind
which gateway route. A Semaphore-driven renderer reads it to deploy vLLM / SGLang / Ollama / ComfyUI
and configure the **bifrost** gateway, the way `tofu-services` reads `netbox-services`. See
**DESIGN.md** for the full decision record (§0), data model, placement/validation rules (§4), and
risks.

**It composes, it does not re-model (DESIGN §0.1):**
- the running inference backend is a `netbox_services.ServiceInstance` — `InferenceDeployment` **FKs
  it** (required, `on_delete=PROTECT`), so `PluginConfig.required_plugins = ["netbox_services"]` and
  the migration depends on `netbox_services.0001_initial` (the `netbox-load-balancing-acl` pattern);
- the GPU card is a core `dcim` record — `GpuDevice` references it via a GFK (Module | InventoryItem)
  and **derives** total VRAM from the `gpu` module-type profile; `netbox-inventory` is *optional*
  asset enrichment, never imported;
- the host is reached transitively through `ServiceInstance.parent`; no direct host FK here.

**Secret policy (load-bearing):** secret *values* never live here. HF tokens / gateway API keys are
OpenBao path references owned by `netbox-services` (`InstanceOpenBaoPath`). Model **weights** are a
registry/object-store *reference* (`ModelCatalog.source` + `source_type`), never a stored blob. Live
GPU telemetry (util, tok·s⁻¹, real VRAM) is **monitoring's** job, not a field here.

**Derive, don't store.** `GpuDevice.vram_total_gb` (from the dcim profile), `GpuDevice
.reserved_vram_gb` (Σ placements), and `InferenceDeployment.estimated_vram_gb` (weights + KV + over‑
head) are **computed properties** — no stored copies, no drift. The only stored VRAM number is the
nullable `vram_total_gb_override` for a card not yet in dcim.

---

## Key Directives / Rules

### DO, ALWAYS:
- If functionality won't work without a parameter, make it a **required positional** parameter.
- Any time you modify a source file, ensure its accompanying test under `netbox_ai/tests/` contains
  **comprehensive tests for the change WITHOUT MOCKS**, so `manage.py test netbox_ai` discovers them.
- Write concise code (avoid obvious comments; one-liners where possible).
- **SPDX header on every source file**: `# SPDX-License-Identifier: AGPL-3.0-or-later`.
- Extract magic numbers (VRAM headroom, KV-cache coefficient, overhead, the gpu VRAM attribute key)
  to `PluginConfig.default_settings` and read them with `get_plugin_config("netbox_ai", …)`.

### DO NOT, EVER:
- Store a secret value, model weights, or live telemetry in a model field.
- Re-model the inference server, the host, or the GPU card — FK/reference them. `netbox-ai` is the
  placement layer *on top of* `ServiceInstance`, never a parallel instance/integration model (the #1
  risk, DESIGN §8).
- Let `extra_args` grow into a JSON blob — it is a bounded `ArrayField` escape hatch; ratchet
  long-tail backend args into typed fields (DESIGN §8).
- Skip a failing test; keep a broken path as a fallback; or re-implement a function to bypass another.
- **Mock the database, the ORM, the NetBox API test client, or any integration path.** Tests run
  against a **real test database** with real `ModelCatalog` / `GpuDevice` / core `dcim.Device` /
  `netbox_services.ServiceInstance` rows.

### Python / Django Guidelines:
- Package-relative imports inside `netbox_ai` (`from .models import GpuDevice`); core/sibling use the
  real path (`from dcim.models import Device`, `from netbox_services.models import ServiceInstance`).
- Models inherit `netbox.models.NetBoxModel` (custom fields, tags, journaling, GraphQL — free).

---

## Architecture (NetBox 4.6 plugin)

| File | Responsibility |
|------|----------------|
| `__init__.py` | `PluginConfig` — name `netbox_ai`, `base_url='ai'`, min/max 4.6, `required_plugins=["netbox_services"]`, `default_settings` (vram_headroom, kv_cache_gb_per_1k_tokens, vram_overhead_gb, gpu_vram_attribute); `ready()` wires `signals` |
| `choices.py` | `ChoiceSet`s: modality, source type, quantization, dtype, KV-cache quant, deployment status (`architecture`/`parameter_count` are free-form by design) |
| `models.py` | the 6 models below + `validate_deployment_placement` |
| `signals.py` | `m2m_changed` backstop on `InferenceDeployment.gpus` re-running `validate_deployment_placement` (catches ORM/seeder/planner writes that bypass the form) |
| `migrations/0001_initial.py` | hand-authored (NetBox disables makemigrations in prod); split CreateModel + AddField for the `GatewayRoute.targets` through-M2M to break the route↔target cycle; depends on `netbox_services.0001_initial` |
| `api/serializers.py`, `api/views.py`, `api/urls.py` | REST (`NetBoxModelViewSet`) — the contract the renderer + seeder read; nests `dcim`/`netbox_services` serializers |
| `filtersets.py` | `NetBoxModelFilterSet` per model |
| `tables.py`, `forms.py`, `navigation.py`, `views.py`, `urls.py` | UI (generic NetBox views) |
| `graphql/__init__.py` | placeholder (auto GraphQL via `NetBoxModel`) |

### Model — catalog + placement + gateway
**Catalog layer** (the model SoT, seeded from `ai-lab/modelfiles/*`):
- **ModelCatalog** (the family): identity + `architecture`/`parameter_count`/`modality` + weights
  *reference* (`source_type` + `source`) + `license` + default/max context.
- **ModelVariant** (FK): one `quant` per row + declared `weights_vram_gb` + `recommended_context`.

**Placement layer** (what the renderer reads):
- **GpuDevice**: FK `dcim.Device` (host) + `index`; GFK `gpu_hardware` (Module | InventoryItem) the
  VRAM is **derived** from; nullable `vram_total_gb_override`; `interconnect_group` (TP eligibility).
  Unique `(device, index)`.
- **InferenceDeployment**: FK `netbox_services.ServiceInstance` (backend, PROTECT) + FK `ModelVariant`
  + M2M `gpus` → GpuDevice; `tensor_parallel`/`pipeline_parallel`, `gpu_memory_utilization`,
  `max_model_len`, `kv_cache_quant`, `dtype`, `served_model_name`, `status`, bounded `extra_args`.
  Validated by `clean()` (range, served-name-per-host) + `validate_deployment_placement` (GPU count
  vs TP×PP, tensor-parallel single-host locality, VRAM budget) via the form and the `m2m_changed`
  backstop.

**Gateway layer** (bifrost):
- **GatewayRoute**: FK `ServiceInstance` (the gateway) + `public_name`; ordered targets via the
  through model. Unique `(service_instance, public_name)`.
- **GatewayRouteTarget** (through): FK `route` + FK `deployment` + `order` (primary = lowest) +
  `weight`. Unique `(route, deployment)`.

### Placement & validation (NetBox validates; an external planner decides — DESIGN §4)
- **VRAM budget:** per GpuDevice, `Σ estimated_vram_gb of touching deployments ≤ vram_total_gb ×
  vram_headroom`. `estimated_vram_gb ≈ (weights + KV-cache + per-shard overhead) / (TP×PP)` — a
  declared estimate with headroom, skipped when a GPU's total is unknown.
- **Tensor-parallel locality:** `tensor_parallel > 1` ⇒ all GPUs on one host / one
  `interconnect_group`. **Pipeline-parallel** may span hosts.
- **GPU count** must equal `tensor_parallel × pipeline_parallel`; `gpu_memory_utilization ∈ (0,1]`;
  `served_model_name` unique per host.

---

## Testing (NO MOCKS — real DB, NetBox test framework)

- Tests live in `netbox_ai/tests/` (`test_models.py`, `test_api.py`, `test_filtersets.py`) with a
  `tests/utils.py` fixture builder over real catalog/GPU/`ServiceInstance`/`dcim.Device` rows.
- **Run**: `python /opt/netbox/app/netbox/manage.py test netbox_ai --keepdb -v2`.
- **Verification owed (cannot run offline — no NetBox env in the build host):**
  `makemigrations netbox_ai --check --dry-run` on an ephemeral NetBox, and a full test run.
  Re-confirm against the pinned NetBox 4.6: the `GpuDevice.gpu_hardware` GFK `limit_choices_to`
  serialization, the `netbox_services.ServiceInstance` FK target + serializer import path, the
  `GatewayRoute.targets` through-M2M migration split, and — load-bearing for VRAM derivation — the
  live netbox-inventory **`gpu` module-type profile's actual VRAM attribute name** (set
  `gpu_vram_attribute` accordingly; DESIGN §8).

---

## Licensing
- **AGPL-3.0-or-later**, SPDX header in every file (SOP → *Code Quality and Testing*).
