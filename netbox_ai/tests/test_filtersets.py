# SPDX-License-Identifier: AGPL-3.0-or-later
"""FilterSet tests over a real DB — representative field filters + the global ``search`` for each
model."""
from django.test import TestCase

from ..filtersets import (
    GatewayRouteFilterSet,
    GpuDeviceFilterSet,
    InferenceDeploymentFilterSet,
    ModelCatalogFilterSet,
    ModelVariantFilterSet,
)
from ..models import GatewayRoute, GpuDevice, InferenceDeployment, ModelCatalog, ModelVariant
from .utils import make_catalog, make_deployment, make_gpu, make_service_instance, make_variant


class ModelCatalogFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_catalog("qwen3-30b", architecture="qwen3", modality="text")
        make_catalog("flux-dev", architecture="flux", modality="image_gen")

    def test_modality(self):
        fs = ModelCatalogFilterSet({"modality": ["image_gen"]}, queryset=ModelCatalog.objects.all())
        self.assertEqual([c.name for c in fs.qs], ["flux-dev"])

    def test_search(self):
        fs = ModelCatalogFilterSet({"q": "qwen"}, queryset=ModelCatalog.objects.all())
        self.assertEqual([c.name for c in fs.qs], ["qwen3-30b"])


class ModelVariantFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("qwen3-30b")
        make_variant(cat, quant="q4_k_m")
        make_variant(cat, quant="fp16")

    def test_quant(self):
        fs = ModelVariantFilterSet({"quant": ["fp16"]}, queryset=ModelVariant.objects.all())
        self.assertEqual(fs.qs.count(), 1)
        self.assertEqual(fs.qs.first().quant, "fp16")

    def test_model_name(self):
        fs = ModelVariantFilterSet({"model": ["qwen3-30b"]}, queryset=ModelVariant.objects.all())
        self.assertEqual(fs.qs.count(), 2)


class GpuDeviceFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_gpu(index=0, interconnect_group="nvlink0")
        make_gpu(index=1, interconnect_group="pcie")

    def test_interconnect_group(self):
        fs = GpuDeviceFilterSet({"interconnect_group": "nvlink0"}, queryset=GpuDevice.objects.all())
        self.assertEqual(fs.qs.count(), 1)


class InferenceDeploymentFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_deployment(served_model_name="qwen-coder", status="active")
        make_deployment(served_model_name="gemma-chat", status="planned")

    def test_status(self):
        fs = InferenceDeploymentFilterSet({"status": ["active"]}, queryset=InferenceDeployment.objects.all())
        self.assertEqual([d.served_model_name for d in fs.qs], ["qwen-coder"])

    def test_search(self):
        fs = InferenceDeploymentFilterSet({"q": "gemma"}, queryset=InferenceDeployment.objects.all())
        self.assertEqual([d.served_model_name for d in fs.qs], ["gemma-chat"])


class GatewayRouteFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        si = make_service_instance(hostname="bifrost", catalog_name="bifrost")
        GatewayRoute.objects.create(service_instance=si, public_name="gpt-4o")
        GatewayRoute.objects.create(service_instance=si, public_name="claude")

    def test_search(self):
        fs = GatewayRouteFilterSet({"q": "gpt"}, queryset=GatewayRoute.objects.all())
        self.assertEqual([r.public_name for r in fs.qs], ["gpt-4o"])
