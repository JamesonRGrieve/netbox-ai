# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generic NetBox CRUD views — one Object/List/Edit/Delete/BulkDelete set per model."""
from netbox.views import generic

from . import filtersets, forms, models, tables


class ModelCatalogView(generic.ObjectView):
    queryset = models.ModelCatalog.objects.all()


class ModelCatalogListView(generic.ObjectListView):
    queryset = models.ModelCatalog.objects.all()
    table = tables.ModelCatalogTable
    filterset = filtersets.ModelCatalogFilterSet
    filterset_form = forms.ModelCatalogFilterForm


class ModelCatalogEditView(generic.ObjectEditView):
    queryset = models.ModelCatalog.objects.all()
    form = forms.ModelCatalogForm


class ModelCatalogDeleteView(generic.ObjectDeleteView):
    queryset = models.ModelCatalog.objects.all()


class ModelCatalogBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ModelCatalog.objects.all()
    table = tables.ModelCatalogTable


class ModelVariantView(generic.ObjectView):
    queryset = models.ModelVariant.objects.all()


class ModelVariantListView(generic.ObjectListView):
    queryset = models.ModelVariant.objects.all()
    table = tables.ModelVariantTable
    filterset = filtersets.ModelVariantFilterSet
    filterset_form = forms.ModelVariantFilterForm


class ModelVariantEditView(generic.ObjectEditView):
    queryset = models.ModelVariant.objects.all()
    form = forms.ModelVariantForm


class ModelVariantDeleteView(generic.ObjectDeleteView):
    queryset = models.ModelVariant.objects.all()


class ModelVariantBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ModelVariant.objects.all()
    table = tables.ModelVariantTable


class GpuDeviceView(generic.ObjectView):
    queryset = models.GpuDevice.objects.all()


class GpuDeviceListView(generic.ObjectListView):
    queryset = models.GpuDevice.objects.all()
    table = tables.GpuDeviceTable
    filterset = filtersets.GpuDeviceFilterSet
    filterset_form = forms.GpuDeviceFilterForm


class GpuDeviceEditView(generic.ObjectEditView):
    queryset = models.GpuDevice.objects.all()
    form = forms.GpuDeviceForm


class GpuDeviceDeleteView(generic.ObjectDeleteView):
    queryset = models.GpuDevice.objects.all()


class GpuDeviceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.GpuDevice.objects.all()
    table = tables.GpuDeviceTable


class InferenceDeploymentView(generic.ObjectView):
    queryset = models.InferenceDeployment.objects.all()


class InferenceDeploymentListView(generic.ObjectListView):
    queryset = models.InferenceDeployment.objects.all()
    table = tables.InferenceDeploymentTable
    filterset = filtersets.InferenceDeploymentFilterSet
    filterset_form = forms.InferenceDeploymentFilterForm


class InferenceDeploymentEditView(generic.ObjectEditView):
    queryset = models.InferenceDeployment.objects.all()
    form = forms.InferenceDeploymentForm


class InferenceDeploymentDeleteView(generic.ObjectDeleteView):
    queryset = models.InferenceDeployment.objects.all()


class InferenceDeploymentBulkDeleteView(generic.BulkDeleteView):
    queryset = models.InferenceDeployment.objects.all()
    table = tables.InferenceDeploymentTable


class GatewayRouteView(generic.ObjectView):
    queryset = models.GatewayRoute.objects.all()


class GatewayRouteListView(generic.ObjectListView):
    queryset = models.GatewayRoute.objects.all()
    table = tables.GatewayRouteTable
    filterset = filtersets.GatewayRouteFilterSet
    filterset_form = forms.GatewayRouteFilterForm


class GatewayRouteEditView(generic.ObjectEditView):
    queryset = models.GatewayRoute.objects.all()
    form = forms.GatewayRouteForm


class GatewayRouteDeleteView(generic.ObjectDeleteView):
    queryset = models.GatewayRoute.objects.all()


class GatewayRouteBulkDeleteView(generic.BulkDeleteView):
    queryset = models.GatewayRoute.objects.all()
    table = tables.GatewayRouteTable


class GatewayRouteTargetView(generic.ObjectView):
    queryset = models.GatewayRouteTarget.objects.all()


class GatewayRouteTargetListView(generic.ObjectListView):
    queryset = models.GatewayRouteTarget.objects.all()
    table = tables.GatewayRouteTargetTable
    filterset = filtersets.GatewayRouteTargetFilterSet
    filterset_form = forms.GatewayRouteTargetFilterForm


class GatewayRouteTargetEditView(generic.ObjectEditView):
    queryset = models.GatewayRouteTarget.objects.all()
    form = forms.GatewayRouteTargetForm


class GatewayRouteTargetDeleteView(generic.ObjectDeleteView):
    queryset = models.GatewayRouteTarget.objects.all()


class GatewayRouteTargetBulkDeleteView(generic.BulkDeleteView):
    queryset = models.GatewayRouteTarget.objects.all()
    table = tables.GatewayRouteTargetTable
