# SPDX-License-Identifier: AGPL-3.0-or-later
"""URL routing — the standard NetBox CRUD + changelog + journal set per model, via a DRY helper."""
from django.urls import path
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from . import models, views


def _routes(slug, name, model, list_view, edit_view, detail_view, delete_view, bulk_delete_view):
    return [
        path(f"{slug}/", list_view.as_view(), name=f"{name}_list"),
        path(f"{slug}/add/", edit_view.as_view(), name=f"{name}_add"),
        path(f"{slug}/delete/", bulk_delete_view.as_view(), name=f"{name}_bulk_delete"),
        path(f"{slug}/<int:pk>/", detail_view.as_view(), name=name),
        path(f"{slug}/<int:pk>/edit/", edit_view.as_view(), name=f"{name}_edit"),
        path(f"{slug}/<int:pk>/delete/", delete_view.as_view(), name=f"{name}_delete"),
        path(f"{slug}/<int:pk>/changelog/", ObjectChangeLogView.as_view(), name=f"{name}_changelog", kwargs={"model": model}),
        path(f"{slug}/<int:pk>/journal/", ObjectJournalView.as_view(), name=f"{name}_journal", kwargs={"model": model}),
    ]


urlpatterns = [
    *_routes("model-catalog", "modelcatalog", models.ModelCatalog,
             views.ModelCatalogListView, views.ModelCatalogEditView, views.ModelCatalogView,
             views.ModelCatalogDeleteView, views.ModelCatalogBulkDeleteView),
    *_routes("model-variants", "modelvariant", models.ModelVariant,
             views.ModelVariantListView, views.ModelVariantEditView, views.ModelVariantView,
             views.ModelVariantDeleteView, views.ModelVariantBulkDeleteView),
    *_routes("gpu-devices", "gpudevice", models.GpuDevice,
             views.GpuDeviceListView, views.GpuDeviceEditView, views.GpuDeviceView,
             views.GpuDeviceDeleteView, views.GpuDeviceBulkDeleteView),
    *_routes("inference-deployments", "inferencedeployment", models.InferenceDeployment,
             views.InferenceDeploymentListView, views.InferenceDeploymentEditView, views.InferenceDeploymentView,
             views.InferenceDeploymentDeleteView, views.InferenceDeploymentBulkDeleteView),
    *_routes("gateway-routes", "gatewayroute", models.GatewayRoute,
             views.GatewayRouteListView, views.GatewayRouteEditView, views.GatewayRouteView,
             views.GatewayRouteDeleteView, views.GatewayRouteBulkDeleteView),
    *_routes("gateway-route-targets", "gatewayroutetarget", models.GatewayRouteTarget,
             views.GatewayRouteTargetListView, views.GatewayRouteTargetEditView, views.GatewayRouteTargetView,
             views.GatewayRouteTargetDeleteView, views.GatewayRouteTargetBulkDeleteView),
]
