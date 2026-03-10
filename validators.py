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

Warning codes
-------------
    W001   topology not declared — defaulted to spine_leaf
    W002   No sites declared
    W003   No devices declared
    W004   No links declared
    W005   Device has no site assigned
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models import TopologyModel, SUPPORTED_TOPOLOGIES, SUPPORTED_STYLE_PROFILES


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

    # ── W002: no sites ────────────────────────────────────────────────────────
    if not model.sites:
        warnings.append(ValidationWarning(
            code    = "W002",
            field   = "sites",
            message = "No sites declared. Site context will be empty for all devices.",
        ))

    declared_sites = {s.name for s in model.sites}

    # ── W003: no devices ──────────────────────────────────────────────────────
    if not model.devices:
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
    if not model.links:
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
            # E004: unknown endpoint
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

    # ── finalise ──────────────────────────────────────────────────────────────
    return ValidationResult(
        ok       = len(errors) == 0,
        errors   = errors,
        warnings = warnings,
    )