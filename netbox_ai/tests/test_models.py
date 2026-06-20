# SPDX-License-Identifier: AGPL-3.0-or-later
"""Model tests over a real DB: catalog identity, derived VRAM (override / reserved), the estimate
arithmetic, and the placement validators (GPU count, tensor-parallel locality, VRAM budget,
served-name-per-host, gpu_memory_utilization range)."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase

from ..choices import ModalityChoices, QuantizationChoices
from ..models import GatewayRoute, GatewayRouteTarget
from .utils import (
    make_catalog,
    make_deployment,
    make_device,
    make_gpu,
    make_service_instance,
    make_variant,
)


class ModelCatalogTest(TestCase):
    def test_str_url_defaults(self):
        catalog = make_catalog("gemma3-27b", display_name="Gemma 3 27B")
        self.assertEqual(str(catalog), "Gemma 3 27B")
        self.assertIn("/plugins/ai/model-catalog/", catalog.get_absolute_url())
        self.assertEqual(catalog.modality, ModalityChoices.TEXT)

    def test_name_unique(self):
        make_catalog("llama3-8b")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_catalog("llama3-8b")


class ModelVariantTest(TestCase):
    def test_str_and_unique(self):
        catalog = make_catalog("qwen3-30b")
        variant = make_variant(catalog, quant=QuantizationChoices.Q4_K_M)
        self.assertEqual(str(variant), "qwen3-30b:q4_k_m")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_variant(catalog, quant=QuantizationChoices.Q4_K_M)


class GpuDeviceVramTest(TestCase):
    def test_override_takes_precedence(self):
        gpu = make_gpu(vram_total_gb_override=24.0)
        self.assertEqual(gpu.vram_total_gb, 24.0)

    def test_unknown_total_is_none(self):
        gpu = make_gpu(vram_total_gb_override=None)
        self.assertIsNone(gpu.vram_total_gb)

    def test_unique_device_index(self):
        gpu = make_gpu(index=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_gpu(device=gpu.device, index=0)

    def test_reserved_vram_is_sum_of_placements(self):
        gpu = make_gpu(vram_total_gb_override=48.0)
        variant = make_variant(weights_vram_gb=10.0)
        make_deployment(variant=variant, served_model_name="a", gpus=[gpu])
        self.assertEqual(gpu.reserved_vram_gb, 11.0)  # 10 weights + 1 overhead, TP/PP=1


class EstimateTest(TestCase):
    def test_estimate_includes_weights_kv_and_overhead(self):
        variant = make_variant(weights_vram_gb=16.0)
        dep = make_deployment(variant=variant, max_model_len=8000)
        # weights 16 + kv (8000/1000 * 0.5 = 4.0) + overhead 1.0 (1 shard) = 21.0
        self.assertEqual(dep.estimated_vram_total_gb, 21.0)
        self.assertEqual(dep.estimated_vram_gb, 21.0)  # 1 shard → per-GPU == total

    def test_tensor_parallel_shards_the_estimate(self):
        variant = make_variant(weights_vram_gb=40.0)
        dep = make_deployment(variant=variant, tensor_parallel=2)
        # total = 40 weights + 0 kv + (1 overhead * 2 shards) = 42; per-GPU = 21
        self.assertEqual(dep.estimated_vram_total_gb, 42.0)
        self.assertEqual(dep.estimated_vram_gb, 21.0)


class PlacementValidationTest(TestCase):
    def test_gpu_count_must_match_parallelism(self):
        dep = make_deployment(tensor_parallel=2, pipeline_parallel=1)
        gpu = make_gpu(index=0)
        with self.assertRaises(ValidationError):
            dep.gpus.set([gpu])  # 1 GPU but TP×PP = 2

    def test_tensor_parallel_requires_single_host(self):
        dep = make_deployment(tensor_parallel=2)
        g0 = make_gpu(device=make_device("host-a"), index=0)
        g1 = make_gpu(device=make_device("host-b"), index=0)
        with self.assertRaises(ValidationError):
            dep.gpus.set([g0, g1])

    def test_tensor_parallel_same_host_ok(self):
        device = make_device("host-tp")
        dep = make_deployment(tensor_parallel=2, variant=make_variant(weights_vram_gb=8.0))
        g0 = make_gpu(device=device, index=0)
        g1 = make_gpu(device=device, index=1)
        dep.gpus.set([g0, g1])
        self.assertEqual(dep.gpus.count(), 2)

    def test_vram_budget_enforced(self):
        gpu = make_gpu(vram_total_gb_override=24.0)  # budget = 24 × 0.9 = 21.6
        big = make_variant(weights_vram_gb=18.0)
        make_deployment(variant=big, served_model_name="first", gpus=[gpu])  # uses 19
        second = make_deployment(variant=big, served_model_name="second")
        with self.assertRaises(ValidationError):
            second.gpus.set([gpu])  # 19 + 19 = 38 > 21.6

    def test_vram_budget_skipped_when_total_unknown(self):
        gpu = make_gpu(vram_total_gb_override=None)
        dep = make_deployment(variant=make_variant(weights_vram_gb=100.0))
        dep.gpus.set([gpu])  # no known total → budget unenforceable, must not raise
        self.assertEqual(dep.gpus.count(), 1)

    def test_served_name_unique_per_host(self):
        device = make_device("shared-host")
        si_a = make_service_instance(device=device, hostname="vllm-a", catalog_name="vllm")
        si_b = make_service_instance(device=device, hostname="vllm-b", catalog_name="sglang")
        make_deployment(service_instance=si_a, served_model_name="gpt-oss")
        clash = make_deployment(service_instance=si_b, served_model_name="gpt-oss")
        with self.assertRaises(ValidationError):
            clash.full_clean()

    def test_gpu_memory_utilization_range(self):
        dep = make_deployment(gpu_memory_utilization=1.5)
        with self.assertRaises(ValidationError):
            dep.full_clean()


class GatewayRouteTest(TestCase):
    def test_route_targets_ordered(self):
        si = make_service_instance(hostname="bifrost", catalog_name="bifrost")
        route = GatewayRoute.objects.create(service_instance=si, public_name="gpt-4o")
        primary = make_deployment(served_model_name="primary")
        fallback = make_deployment(served_model_name="fallback")
        GatewayRouteTarget.objects.create(route=route, deployment=fallback, order=200)
        GatewayRouteTarget.objects.create(route=route, deployment=primary, order=100)
        ordered = list(route.route_targets.all())
        self.assertEqual(ordered[0].deployment, primary)
        self.assertEqual(str(route), "gpt-4o")

    def test_public_name_unique_per_gateway(self):
        si = make_service_instance(hostname="bifrost", catalog_name="bifrost")
        GatewayRoute.objects.create(service_instance=si, public_name="claude")
        with self.assertRaises(IntegrityError), transaction.atomic():
            GatewayRoute.objects.create(service_instance=si, public_name="claude")
