# SPDX-License-Identifier: AGPL-3.0-or-later
"""ORM backstop for placement validation. ``InferenceDeploymentForm.clean`` covers the form path;
this ``m2m_changed`` receiver catches direct ORM / seeder / planner writes (``deployment.gpus.set``)
that bypass the form, re-running :func:`validate_deployment_placement` against the resulting GPU set.
Connected in :meth:`NetBoxAIConfig.ready`. The VRAM budget is a cross-row count check (not a DB
constraint), so it is validation-only and can race under truly-concurrent writes (documented;
acceptable — the planner is the single writer)."""
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import InferenceDeployment, validate_deployment_placement


@receiver(m2m_changed, sender=InferenceDeployment.gpus.through)
def _validate_deployment_gpus(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        validate_deployment_placement(instance, instance.gpus.all())
