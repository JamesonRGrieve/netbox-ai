# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST API CRUD tests against a real DB + real API client (no mocks). Composes the explicit CRUD
mixins; FK payloads are PKs (NetBox nested serializers accept a PK on write). create_data for the
deployment uses a dedicated backend/host so served-name-per-host uniqueness never collides with the
list fixtures."""
from utilities.testing import APIViewTestCases

from ..models import (
    GatewayRoute,
    GatewayRouteTarget,
    GpuDevice,
    InferenceDeployment,
    ModelCatalog,
    ModelVariant,
)
from .utils import make_catalog, make_device, make_service_instance, make_variant


class _CRUD(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    pass


class ModelCatalogAPITest(_CRUD):
    model = ModelCatalog
    brief_fields = ["display", "display_name", "id", "name", "url"]
    bulk_update_data = {"license": "MIT"}

    @classmethod
    def setUpTestData(cls):
        for n in ("qwen3-30b", "gemma3-27b", "llama3-8b"):
            make_catalog(n)
        cls.create_data = [
            {"name": "flux-dev", "display_name": "Flux Dev", "source": "hf.co/black-forest-labs/flux"},
            {"name": "mistral-small", "display_name": "Mistral Small", "source": "hf.co/mistralai/small"},
            {"name": "phi4", "display_name": "Phi 4", "source": "ollama:phi4"},
        ]


class ModelVariantAPITest(_CRUD):
    model = ModelVariant
    brief_fields = ["display", "id", "model", "quant", "url"]
    bulk_update_data = {"recommended_context": 4096}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("qwen3-coder-30b")
        for q in ("q4_k_m", "q8_0", "fp16"):
            make_variant(cat, quant=q)
        cls.create_data = [
            {"model": cat.pk, "quant": "awq", "weights_vram_gb": 18.0},
            {"model": cat.pk, "quant": "gptq", "weights_vram_gb": 17.0},
            {"model": cat.pk, "quant": "fp8", "weights_vram_gb": 30.0},
        ]


class GpuDeviceAPITest(_CRUD):
    model = GpuDevice
    brief_fields = ["device", "display", "id", "index", "url"]
    bulk_update_data = {"interconnect_group": "nvlink0"}

    @classmethod
    def setUpTestData(cls):
        device = make_device("gpu-api-host")
        for i in range(3):
            GpuDevice.objects.create(device=device, index=i, vram_total_gb_override=24.0)
        cls.create_data = [
            {"device": device.pk, "index": 3, "vram_total_gb_override": 24.0},
            {"device": device.pk, "index": 4, "vram_total_gb_override": 24.0},
            {"device": device.pk, "index": 5, "vram_total_gb_override": 48.0},
        ]


class InferenceDeploymentAPITest(_CRUD):
    model = InferenceDeployment
    brief_fields = ["display", "id", "served_model_name", "status", "url"]
    bulk_update_data = {"status": "active"}

    @classmethod
    def setUpTestData(cls):
        variant = make_variant()
        existing = make_service_instance(hostname="vllm-list", catalog_name="vllm")
        for n in ("d1", "d2", "d3"):
            InferenceDeployment.objects.create(service_instance=existing, variant=variant, served_model_name=n)
        backend = make_service_instance(hostname="vllm-create", catalog_name="sglang")
        cls.create_data = [
            {"service_instance": backend.pk, "variant": variant.pk, "served_model_name": "c1"},
            {"service_instance": backend.pk, "variant": variant.pk, "served_model_name": "c2"},
            {"service_instance": backend.pk, "variant": variant.pk, "served_model_name": "c3"},
        ]


class GatewayRouteAPITest(_CRUD):
    model = GatewayRoute
    brief_fields = ["display", "id", "public_name", "url"]
    bulk_update_data = {"rate_limit": 120}

    @classmethod
    def setUpTestData(cls):
        gateway = make_service_instance(hostname="bifrost", catalog_name="bifrost")
        for n in ("gpt-4o", "claude", "llama"):
            GatewayRoute.objects.create(service_instance=gateway, public_name=n)
        cls.create_data = [
            {"service_instance": gateway.pk, "public_name": "qwen"},
            {"service_instance": gateway.pk, "public_name": "gemma"},
            {"service_instance": gateway.pk, "public_name": "mistral"},
        ]


class GatewayRouteTargetAPITest(_CRUD):
    model = GatewayRouteTarget
    brief_fields = ["deployment", "display", "id", "order", "url"]
    bulk_update_data = {"weight": 5}

    @classmethod
    def setUpTestData(cls):
        gateway = make_service_instance(hostname="bifrost", catalog_name="bifrost")
        route = GatewayRoute.objects.create(service_instance=gateway, public_name="gpt-4o")
        backend = make_service_instance(hostname="vllm-rt", catalog_name="vllm")
        variant = make_variant()
        deployments = [
            InferenceDeployment.objects.create(
                service_instance=backend, variant=variant, served_model_name=f"rt-{i}"
            )
            for i in range(6)
        ]
        for i in range(3):
            GatewayRouteTarget.objects.create(route=route, deployment=deployments[i], order=100 + i)
        cls.create_data = [
            {"route": route.pk, "deployment": deployments[3].pk, "order": 200, "weight": 1},
            {"route": route.pk, "deployment": deployments[4].pk, "order": 300, "weight": 2},
            {"route": route.pk, "deployment": deployments[5].pk, "order": 400, "weight": 3},
        ]
