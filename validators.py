# -*- coding: utf-8 -*-
"""
validators.py — Schema validation for TopologyModel before diagram build.

Validation is strict: if any errors are found the build is refused entirely.
Warnings are collected and returned alongside a successful build but never
block it.

All issues are collected in a single pass — the caller always receives the
complete list of problems, not just the first one encountered.

Public API
----------
    validate(model)        -> ValidationResult
    ValidationResult       — dataclass holding errors, warnings, and ok flag
    ValidationError        — a single error entry
    ValidationWarning      — a single warning entry

Error codes
-----------
    E001   Unknown device role
    E002   Duplicate device hostname
    E003   Empty device hostname
    E004   Link endpoint references unknown hostname
    E005   Empty link endpoint (a or b)
    E006   Unsupported topology type
    E007   Unsupported style profile
    E008   Device references undeclared site
    E009   Unsupported hub_spoke mode
    E010   Container member references unknown hostname
    E011   Duplicate site name (multi_site)
    E012   Unsupported interconnect type (multi_site)
    E013   Site has zero spines (multi_site)
    E014   Site has zero leafs (multi_site)

Warning codes
-------------
    W001   topology not declared — defaulted to spine_leaf
    W002   No sites declared
    W003   No devices declared
    W004   No links declared
    W005   Device has no site assigned
    W006   hub_spoke topology_mode not declared — defaulted
    W007   No interconnect type declared for multi_site — defaulted
    W008   multi_site topology has fewer than 2 sites
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models import (
    TopologyModel,
    SUPPORTED_TOPOLOGIES,
    SUPPORTED_STYLE_PROFILES,
    SUPPORTED_HUB_SPOKE_MODES,
)
from drawio import SUPPORTED_INTERCONNECT_TYPES


# ==============================================================================
# RESULT TYPES
# ==============================================================================

@dataclass
class ValidationError:
    """A single validation error that blocks the build."""
    code:    str   # e.g. "E001"
    field:   str   # e.g. "devices[2].role"
    message: str


@dataclass
class ValidationWarning:
    """A single validation warning that does not block the build."""
    code:    str   # e.g. "W001"
    field:   str
    message: str


@dataclass
class ValidationResult:
    """
    The outcome of a validate() call.

    Attributes:
        ok:       True if no errors were found (warnings are allowed).
        errors:   List of ValidationError entries — empty on success.
        warnings: List of ValidationWarning entries — may be non-empty on success.
    """
    ok:       bool                    = True
    errors:   list[ValidationError]   = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "status":   "ok" if self.ok else "error",
            "errors":   [
                {"code": e.code, "field": e.field, "message": e.message}
                for e in self.errors
            ],
            "warnings": [
                {"code": w.code, "field": w.field, "message": w.message}
                for w in self.warnings
            ],
        }


# ==============================================================================
# VALIDATOR
# ==============================================================================

def validate(model: TopologyModel) -> ValidationResult:
    """
    Validate a TopologyModel and return a ValidationResult.

    All errors and warnings are collected in a single pass.
    The result's ``ok`` flag is False if any errors were found.

    Args:
        model: A parsed TopologyModel from models.load_model().

    Returns:
        A ValidationResult with a complete list of errors and warnings.
    """
    from drawio import ROLE_LAYER   # imported here to avoid circular imports

    errors:   list[ValidationError]   = []
    warnings: list[ValidationWarning] = []

    # ── W001: topology defaulted ───────────────────────────────────────────────
    if model.meta.topology_defaulted:
        warnings.append(ValidationWarning(
            code    = "W001",
            field   = "meta.topology",
            message = (
                f"topology not declared in YAML — defaulted to "
                f"'{model.meta.topology}'. "
                f"Supported topologies: {', '.join(sorted(SUPPORTED_TOPOLOGIES))}."
            ),
        ))

    # ── E006: unsupported topology ─────────────────────────────────────────────
    if model.meta.topology not in SUPPORTED_TOPOLOGIES:
        errors.append(ValidationError(
            code    = "E006",
            field   = "meta.topology",
            message = (
                f"Unsupported topology '{model.meta.topology}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TOPOLOGIES))}."
            ),
        ))

    # ── E007: unsupported style profile ───────────────────────────────────────
    if model.meta.style_profile not in SUPPORTED_STYLE_PROFILES:
        errors.append(ValidationError(
            code    = "E007",
            field   = "meta.style_profile",
            message = (
                f"Unsupported style profile '{model.meta.style_profile}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_STYLE_PROFILES))}."
            ),
        ))

    # ── E009: unsupported hub_spoke mode ──────────────────────────────────────
    if (model.meta.topology == "hub_spoke"
            and model.meta.topology_mode
            and model.meta.topology_mode not in SUPPORTED_HUB_SPOKE_MODES):
        errors.append(ValidationError(
            code    = "E009",
            field   = "meta.topology_mode",
            message = (
                f"Unsupported hub_spoke mode '{model.meta.topology_mode}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_HUB_SPOKE_MODES))}."
            ),
        ))

    # ── W006: hub_spoke mode not declared — will default ──────────────────────
    if (model.meta.topology == "hub_spoke"
            and not model.meta.topology_mode):
        warnings.append(ValidationWarning(
            code    = "W006",
            field   = "meta.topology_mode",
            message = (
                "topology_mode not declared for hub_spoke — defaulting to 'tenant_fabric'. "
                f"Supported modes: {', '.join(sorted(SUPPORTED_HUB_SPOKE_MODES))}."
            ),
        ))

    # ── multi_site checks ─────────────────────────────────────────────────────
    if model.meta.topology == "multi_site":

        # E011 — duplicate site name
        seen_sites: set[str] = set()
        for i, s in enumerate(model.site_specs):
            if s.name in seen_sites:
                errors.append(ValidationError(
                    code    = "E011",
                    field   = f"sites[{i}].name",
                    message = f"Duplicate site name: '{s.name}'.",
                ))
            seen_sites.add(s.name)

        # E012 — invalid interconnect type
        if model.interconnect.type not in SUPPORTED_INTERCONNECT_TYPES:
            errors.append(ValidationError(
                code    = "E012",
                field   = "interconnect.type",
                message = (
                    f"Unsupported interconnect type: '{model.interconnect.type}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_INTERCONNECT_TYPES))}."
                ),
            ))

        # E013 — site has zero spines
        for i, s in enumerate(model.site_specs):
            if s.spines < 1:
                errors.append(ValidationError(
                    code    = "E013",
                    field   = f"sites[{i}].spines",
                    message = (
                        f"Site '{s.name}' must have at least 1 spine (got {s.spines})."
                    ),
                ))

        # E014 — site has zero leafs
        for i, s in enumerate(model.site_specs):
            if s.leafs < 1:
                errors.append(ValidationError(
                    code    = "E014",
                    field   = f"sites[{i}].leafs",
                    message = (
                        f"Site '{s.name}' must have at least 1 leaf (got {s.leafs})."
                    ),
                ))

        # W007 — no interconnect type declared (empty string)
        if not model.interconnect.type:
            warnings.append(ValidationWarning(
                code    = "W007",
                field   = "interconnect.type",
                message = (
                    "No interconnect type declared for multi_site topology; "
                    "defaulted to 'evpn'."
                ),
            ))

        # W008 — fewer than 2 sites
        if len(model.site_specs) < 2:
            warnings.append(ValidationWarning(
                code    = "W008",
                field   = "sites",
                message = (
                    "multi_site topology has fewer than 2 sites — "
                    "consider using spine_leaf instead."
                ),
            ))

    # ── W002: no sites ────────────────────────────────────────────────────────
    if not model.sites and model.meta.topology != "multi_site":
        warnings.append(ValidationWarning(
            code    = "W002",
            field   = "sites",
            message = "No sites declared. Site context will be empty for all devices.",
        ))

    declared_sites = {s.name for s in model.sites}

    # ── W003: no devices ──────────────────────────────────────────────────────
    if not model.devices and model.meta.topology != "multi_site":
        warnings.append(ValidationWarning(
            code    = "W003",
            field   = "devices",
            message = "No devices declared. The diagram will be empty.",
        ))

    # ── device-level checks ───────────────────────────────────────────────────
    seen_hostnames: set[str] = set()

    for i, device in enumerate(model.devices):
        ref = f"devices[{i}]"

        # E003: empty hostname
        if not device.hostname.strip():
            errors.append(ValidationError(
                code    = "E003",
                field   = f"{ref}.hostname",
                message = f"Device at index {i} has an empty hostname.",
            ))
            continue   # skip further checks for this entry

        # E002: duplicate hostname
        if device.hostname in seen_hostnames:
            errors.append(ValidationError(
                code    = "E002",
                field   = f"{ref}.hostname",
                message = f"Duplicate hostname '{device.hostname}'. Hostnames must be unique.",
            ))
        else:
            seen_hostnames.add(device.hostname)

        # E001: unknown role
        if device.role not in ROLE_LAYER:
            errors.append(ValidationError(
                code    = "E001",
                field   = f"{ref}.role",
                message = (
                    f"Unknown role '{device.role}' for device '{device.hostname}'. "
                    f"Valid roles: {', '.join(sorted(ROLE_LAYER.keys()))}."
                ),
            ))

        # W005: no site assigned
        if not device.site.strip():
            warnings.append(ValidationWarning(
                code    = "W005",
                field   = f"{ref}.site",
                message = f"Device '{device.hostname}' has no site assigned.",
            ))

        # E008: site not declared
        elif declared_sites and device.site not in declared_sites:
            errors.append(ValidationError(
                code    = "E008",
                field   = f"{ref}.site",
                message = (
                    f"Device '{device.hostname}' references undeclared site "
                    f"'{device.site}'. Declared sites: "
                    f"{', '.join(sorted(declared_sites))}."
                ),
            ))

    # ── W004: no links ────────────────────────────────────────────────────────
    if not model.links and model.meta.topology != "multi_site":
        warnings.append(ValidationWarning(
            code    = "W004",
            field   = "links",
            message = "No links declared. Devices will be placed with no connections.",
        ))

    # ── link-level checks ─────────────────────────────────────────────────────
    for i, link in enumerate(model.links):
        ref = f"links[{i}]"

        # E005: empty endpoint
        if not link.a.strip():
            errors.append(ValidationError(
                code    = "E005",
                field   = f"{ref}.a",
                message = f"Link at index {i} has an empty 'a' endpoint.",
            ))
        elif link.a not in seen_hostnames:
            errors.append(ValidationError(
                code    = "E004",
                field   = f"{ref}.a",
                message = (
                    f"Link endpoint '{link.a}' does not match any declared "
                    f"device hostname."
                ),
            ))

        if not link.b.strip():
            errors.append(ValidationError(
                code    = "E005",
                field   = f"{ref}.b",
                message = f"Link at index {i} has an empty 'b' endpoint.",
            ))
        elif link.b not in seen_hostnames:
            errors.append(ValidationError(
                code    = "E004",
                field   = f"{ref}.b",
                message = (
                    f"Link endpoint '{link.b}' does not match any declared "
                    f"device hostname."
                ),
            ))

    # ── container member checks ───────────────────────────────────────────────
    for i, container in enumerate(model.containers):
        ref = f"containers[{i}]"
        for j, member in enumerate(container.members):
            if member not in seen_hostnames:
                errors.append(ValidationError(
                    code    = "E010",
                    field   = f"{ref}.members[{j}]",
                    message = (
                        f"Container '{container.name}' member '{member}' does not "
                        f"match any declared device hostname."
                    ),
                ))

    # ── finalise ──────────────────────────────────────────────────────────────
    return ValidationResult(
        ok       = len(errors) == 0,
        errors   = errors,
        warnings = warnings,
    )