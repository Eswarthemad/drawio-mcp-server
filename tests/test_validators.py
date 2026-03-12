"""
tests/test_validators.py
Unit tests for validators.py — every error code and warning code.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import TopologyModel, DiagramMeta, Device, Link, Site, Container
from validators import validate, ValidationResult


# ==============================================================================
# Helpers
# ==============================================================================

def make_model(
    topology: str = "spine_leaf",
    topology_mode: str = "",
    style_profile: str = "minimal",
    topology_defaulted: bool = False,
    devices: list | None = None,
    links: list | None = None,
    sites: list | None = None,
    containers: list | None = None,
) -> TopologyModel:
    meta = DiagramMeta(
        name=               "Test",
        topology=           topology,
        topology_mode=      topology_mode,
        style_profile=      style_profile,
        topology_defaulted= topology_defaulted,
    )
    return TopologyModel(
        meta=       meta,
        devices=    devices    or [],
        links=      links      or [],
        sites=      sites      or [],
        containers= containers or [],
    )


def device(hostname: str, role: str, site: str = "") -> Device:
    return Device(hostname=hostname, role=role, site=site)


def link(a: str, b: str, link_type: str = "fabric") -> Link:
    return Link(a=a, b=b, type=link_type)


def assert_error(result: ValidationResult, code: str) -> None:
    codes = [e.code for e in result.errors]
    assert code in codes, f"Expected error {code}, got: {codes}"


def assert_warning(result: ValidationResult, code: str) -> None:
    codes = [w.code for w in result.warnings]
    assert code in codes, f"Expected warning {code}, got: {codes}"


def assert_no_error(result: ValidationResult, code: str) -> None:
    codes = [e.code for e in result.errors]
    assert code not in codes, f"Unexpected error {code}"


# ==============================================================================
# Clean model — baseline
# ==============================================================================

class TestCleanModel:

    def test_valid_model_passes(self):
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[
                device("spine01", "spine", "DC1"),
                device("leaf01",  "leaf",  "DC1"),
            ],
            links=[link("spine01", "leaf01")],
        )
        result = validate(model)
        assert result.ok is True
        assert result.errors == []

    def test_result_to_dict_ok(self):
        model = make_model(
            devices=[device("spine01", "spine")],
            sites=[Site(name="DC1")],
        )
        result = validate(model)
        d = result.to_dict()
        assert "status" in d
        assert "errors" in d
        assert "warnings" in d


# ==============================================================================
# Error codes
# ==============================================================================

class TestErrorE001:
    """E001 — unknown device role."""

    def test_unknown_role_triggers_e001(self):
        model = make_model(devices=[device("x", "superswitch")])
        result = validate(model)
        assert_error(result, "E001")

    def test_known_role_no_e001(self):
        model = make_model(devices=[device("x", "spine")])
        result = validate(model)
        assert_no_error(result, "E001")


class TestErrorE002:
    """E002 — duplicate hostname."""

    def test_duplicate_hostname_triggers_e002(self):
        model = make_model(devices=[
            device("spine01", "spine"),
            device("spine01", "leaf"),
        ])
        result = validate(model)
        assert_error(result, "E002")

    def test_unique_hostnames_no_e002(self):
        model = make_model(devices=[
            device("spine01", "spine"),
            device("spine02", "spine"),
        ])
        result = validate(model)
        assert_no_error(result, "E002")


class TestErrorE003:
    """E003 — empty hostname."""

    def test_empty_hostname_triggers_e003(self):
        model = make_model(devices=[device("", "spine")])
        result = validate(model)
        assert_error(result, "E003")

    def test_whitespace_hostname_triggers_e003(self):
        model = make_model(devices=[device("   ", "spine")])
        result = validate(model)
        assert_error(result, "E003")


class TestErrorE004:
    """E004 — link endpoint references unknown hostname."""

    def test_unknown_link_endpoint_a(self):
        model = make_model(
            devices=[device("leaf01", "leaf")],
            links=[link("ghost01", "leaf01")],
        )
        result = validate(model)
        assert_error(result, "E004")

    def test_unknown_link_endpoint_b(self):
        model = make_model(
            devices=[device("spine01", "spine")],
            links=[link("spine01", "ghost99")],
        )
        result = validate(model)
        assert_error(result, "E004")

    def test_known_endpoints_no_e004(self):
        model = make_model(
            devices=[device("spine01", "spine"), device("leaf01", "leaf")],
            links=[link("spine01", "leaf01")],
        )
        result = validate(model)
        assert_no_error(result, "E004")


class TestErrorE005:
    """E005 — empty link endpoint."""

    def test_empty_a_endpoint(self):
        model = make_model(
            devices=[device("leaf01", "leaf")],
            links=[link("", "leaf01")],
        )
        result = validate(model)
        assert_error(result, "E005")

    def test_empty_b_endpoint(self):
        model = make_model(
            devices=[device("spine01", "spine")],
            links=[link("spine01", "")],
        )
        result = validate(model)
        assert_error(result, "E005")


class TestErrorE006:
    """E006 — unsupported topology."""

    def test_unknown_topology_triggers_e006(self):
        model = make_model(topology="alien_topology")
        result = validate(model)
        assert_error(result, "E006")

    def test_spine_leaf_no_e006(self):
        model = make_model(topology="spine_leaf")
        result = validate(model)
        assert_no_error(result, "E006")

    def test_hub_spoke_no_e006(self):
        model = make_model(topology="hub_spoke")
        result = validate(model)
        assert_no_error(result, "E006")

    def test_security_stack_no_e006(self):
        model = make_model(topology="security_stack")
        result = validate(model)
        assert_no_error(result, "E006")


class TestErrorE007:
    """E007 — unsupported style profile."""

    def test_unknown_profile_triggers_e007(self):
        model = make_model(style_profile="neon_pink")
        result = validate(model)
        assert_error(result, "E007")

    def test_all_valid_profiles_no_e007(self):
        for profile in ("minimal", "enterprise", "dark", "vendor-neutral"):
            model = make_model(style_profile=profile)
            result = validate(model)
            assert_no_error(result, "E007")


class TestErrorE008:
    """E008 — device references undeclared site."""

    def test_undeclared_site_triggers_e008(self):
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[device("spine01", "spine", site="DC99")],
        )
        result = validate(model)
        assert_error(result, "E008")

    def test_declared_site_no_e008(self):
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[device("spine01", "spine", site="DC1")],
        )
        result = validate(model)
        assert_no_error(result, "E008")

    def test_empty_site_no_e008(self):
        """Device with empty site should not trigger E008."""
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[device("spine01", "spine", site="")],
        )
        result = validate(model)
        assert_no_error(result, "E008")


class TestErrorE009:
    """E009 — unsupported hub_spoke mode."""

    def test_bad_hub_spoke_mode_triggers_e009(self):
        model = make_model(topology="hub_spoke", topology_mode="star_wars_mode")
        result = validate(model)
        assert_error(result, "E009")

    def test_tenant_fabric_mode_no_e009(self):
        model = make_model(topology="hub_spoke", topology_mode="tenant_fabric")
        result = validate(model)
        assert_no_error(result, "E009")

    def test_wan_branch_mode_no_e009(self):
        model = make_model(topology="hub_spoke", topology_mode="wan_branch")
        result = validate(model)
        assert_no_error(result, "E009")

    def test_non_hub_spoke_topology_with_mode_no_e009(self):
        """E009 only fires for hub_spoke topology."""
        model = make_model(topology="spine_leaf", topology_mode="bad_mode")
        result = validate(model)
        assert_no_error(result, "E009")


class TestErrorE010:
    """E010 — container member references unknown hostname."""

    def test_unknown_container_member_triggers_e010(self):
        model = make_model(
            devices=[device("spine01", "spine")],
            containers=[Container(name="Zone", members=["ghost_host"])],
        )
        result = validate(model)
        assert_error(result, "E010")

    def test_known_container_member_no_e010(self):
        model = make_model(
            devices=[device("spine01", "spine")],
            containers=[Container(name="Zone", members=["spine01"])],
        )
        result = validate(model)
        assert_no_error(result, "E010")


# ==============================================================================
# Warning codes
# ==============================================================================

class TestWarningW001:
    """W001 — topology defaulted."""

    def test_topology_defaulted_triggers_w001(self):
        model = make_model(topology_defaulted=True)
        result = validate(model)
        assert_warning(result, "W001")

    def test_topology_declared_no_w001(self):
        model = make_model(topology_defaulted=False)
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W001" not in codes


class TestWarningW002:
    """W002 — no sites declared."""

    def test_no_sites_triggers_w002(self):
        model = make_model(sites=[])
        result = validate(model)
        assert_warning(result, "W002")

    def test_with_sites_no_w002(self):
        model = make_model(sites=[Site(name="DC1")])
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W002" not in codes


class TestWarningW003:
    """W003 — no devices declared."""

    def test_no_devices_triggers_w003(self):
        model = make_model(devices=[])
        result = validate(model)
        assert_warning(result, "W003")

    def test_with_devices_no_w003(self):
        model = make_model(devices=[device("spine01", "spine")])
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W003" not in codes


class TestWarningW004:
    """W004 — no links declared."""

    def test_no_links_triggers_w004(self):
        model = make_model(links=[])
        result = validate(model)
        assert_warning(result, "W004")

    def test_with_links_no_w004(self):
        model = make_model(
            devices=[device("spine01", "spine"), device("leaf01", "leaf")],
            links=[link("spine01", "leaf01")],
        )
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W004" not in codes


class TestWarningW005:
    """W005 — device has no site assigned."""

    def test_device_with_no_site_triggers_w005(self):
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[device("spine01", "spine", site="")],
        )
        result = validate(model)
        assert_warning(result, "W005")

    def test_device_with_site_no_w005(self):
        model = make_model(
            sites=[Site(name="DC1")],
            devices=[device("spine01", "spine", site="DC1")],
        )
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W005" not in codes


class TestWarningW006:
    """W006 — hub_spoke mode not declared."""

    def test_hub_spoke_without_mode_triggers_w006(self):
        model = make_model(topology="hub_spoke", topology_mode="")
        result = validate(model)
        assert_warning(result, "W006")

    def test_hub_spoke_with_mode_no_w006(self):
        model = make_model(topology="hub_spoke", topology_mode="tenant_fabric")
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W006" not in codes

    def test_spine_leaf_no_w006(self):
        """W006 should not fire for non-hub_spoke topologies."""
        model = make_model(topology="spine_leaf", topology_mode="")
        result = validate(model)
        codes = [w.code for w in result.warnings]
        assert "W006" not in codes


# ==============================================================================
# Full collection — all errors in single pass
# ==============================================================================

class TestFullCollection:

    def test_multiple_errors_collected_in_one_pass(self):
        """All errors should be collected — not just the first one."""
        model = make_model(
            topology="bad_topology",
            style_profile="bad_profile",
            devices=[
                device("", "unknown_role"),      # E001, E003
                device("dupe", "spine"),
                device("dupe", "leaf"),           # E002
            ],
            links=[link("ghost", "also_ghost")], # E004 × 2
        )
        result = validate(model)
        assert result.ok is False
        # Must collect all, not short-circuit
        assert len(result.errors) >= 3

    def test_warnings_do_not_block_build(self):
        """A model with only warnings should still have ok=True."""
        model = make_model(
            topology_defaulted=True,  # W001
            sites=[],                  # W002
            devices=[],                # W003
            links=[],                  # W004
        )
        result = validate(model)
        assert result.ok is True
        assert len(result.warnings) >= 3