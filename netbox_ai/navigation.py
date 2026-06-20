# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plugin navigation — Catalog (model SoT), Placement (GPUs + deployments), Gateway (bifrost)."""
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


def _item(model, label):
    return PluginMenuItem(
        link=f"plugins:netbox_ai:{model}_list",
        link_text=label,
        buttons=[PluginMenuButton(f"plugins:netbox_ai:{model}_add", "Add", "mdi mdi-plus-thick")],
    )


menu = PluginMenu(
    label="AI",
    groups=(
        ("Catalog", (_item("modelcatalog", "Model Catalog"), _item("modelvariant", "Model Variants"))),
        ("Placement", (_item("gpudevice", "GPU Devices"), _item("inferencedeployment", "Inference Deployments"))),
        ("Gateway", (_item("gatewayroute", "Gateway Routes"), _item("gatewayroutetarget", "Route Targets"))),
    ),
    icon_class="mdi mdi-brain",
)
