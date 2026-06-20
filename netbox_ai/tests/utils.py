# SPDX-License-Identifier: AGPL-3.0-or-later
"""Idempotent fixture builders for the netbox-ai test suite — real catalog/variant/GPU/deployment
rows over a real ``netbox_services.ServiceInstance`` on a real core ``dcim.Device`` (no mocks). A
monotonic counter uniquifies the auto-generated names so a single test can build several fixtures
without tripping the unique constraints; callers that assert on a name pass it explicitly."""
import itertools

from netbox_services.models import ServiceCatalog, ServiceInstance
from utilities.testing import create_test_device

from ..models import GpuDevice, InferenceDeployment, ModelCatalog, ModelVariant

_seq = itertools.count(1)


def make_catalog(name="qwen3-coder-30b", **kwargs):
    defaults = {"display_name": name.title(), "source": f"hf.co/{name}"}
    defaults.update(kwargs)
    return ModelCatalog.objects.create(name=name, **defaults)


def make_variant(catalog=None, quant="q4_k_m", weights_vram_gb=18.0, **kwargs):
    catalog = catalog or make_catalog(f"model-{next(_seq)}")
    return ModelVariant.objects.create(model=catalog, quant=quant, weights_vram_gb=weights_vram_gb, **kwargs)


def make_device(name=None):
    return create_test_device(name or f"device-{next(_seq)}")


def make_service_instance(device=None, hostname=None, catalog_name="vllm"):
    hostname = hostname or f"host-{next(_seq)}"
    device = device or make_device(f"dev-{hostname}")
    catalog, _ = ServiceCatalog.objects.get_or_create(
        name=catalog_name, defaults={"display_name": catalog_name.title()}
    )
    return ServiceInstance.objects.create(catalog=catalog, parent=device, hostname=hostname)


def make_gpu(device=None, index=0, vram_total_gb_override=24.0, interconnect_group="", **kwargs):
    device = device or make_device()
    return GpuDevice.objects.create(
        device=device, index=index, vram_total_gb_override=vram_total_gb_override,
        interconnect_group=interconnect_group, **kwargs
    )


def make_deployment(service_instance=None, variant=None, served_model_name="qwen", gpus=None, **kwargs):
    service_instance = service_instance or make_service_instance()
    variant = variant or make_variant()
    deployment = InferenceDeployment.objects.create(
        service_instance=service_instance, variant=variant, served_model_name=served_model_name, **kwargs
    )
    if gpus:
        deployment.gpus.set(gpus)
    return deployment
