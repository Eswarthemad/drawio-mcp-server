"""
tests/test_styles.py
Unit tests for styles.py — all 4 profiles × all roles, edge/container styles.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from styles import (
    resolve_node_style,
    resolve_edge_style,
    resolve_container_style,
)
from models import SUPPORTED_STYLE_PROFILES
from drawio import ROLE_LAYER

ALL_ROLES = list(ROLE_LAYER.keys())
ALL_PROFILES = list(SUPPORTED_STYLE_PROFILES)
ALL_LINK_TYPES = ["fabric", "uplink", "management", "wan", "default"]


# ==============================================================================
# resolve_node_style
# ==============================================================================

class TestResolveNodeStyle:

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_all_roles_return_string_minimal(self, role):
        result = resolve_node_style(role, "minimal")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("profile", ALL_PROFILES)
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_all_roles_all_profiles(self, role, profile):
        """Every role × profile combination must return a non-empty string."""
        result = resolve_node_style(role, profile)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_role_returns_fallback(self):
        """Unknown role should return a fallback style, not raise."""
        result = resolve_node_style("totally_made_up_role", "minimal")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_profile_falls_back_to_minimal(self):
        """Unknown profile should silently fall back to minimal."""
        result = resolve_node_style("spine", "nonexistent_profile")
        minimal = resolve_node_style("spine", "minimal")
        assert result == minimal

    def test_spine_minimal_contains_fillcolor(self):
        result = resolve_node_style("spine", "minimal")
        assert "fillColor" in result

    def test_firewall_minimal_distinct_from_spine(self):
        """Firewall and spine should have different styles in minimal."""
        fw    = resolve_node_style("firewall", "minimal")
        spine = resolve_node_style("spine", "minimal")
        assert fw != spine

    def test_dark_profile_contains_white_text(self):
        """Dark profile spine should have white font colour."""
        result = resolve_node_style("spine", "dark")
        assert "ffffff" in result.lower() or "fontColor" in result

    def test_phase4_roles_have_styles(self):
        """Phase 4 roles must have real styles in all profiles."""
        phase4_roles = [
            "internet", "application_server", "database_node",
            "wan_router", "branch_router",
        ]
        for role in phase4_roles:
            for profile in ALL_PROFILES:
                result = resolve_node_style(role, profile)
                assert len(result) > 0, f"Empty style for {role}/{profile}"


# ==============================================================================
# resolve_edge_style
# ==============================================================================

class TestResolveEdgeStyle:

    @pytest.mark.parametrize("link_type", ALL_LINK_TYPES)
    def test_all_link_types_return_string(self, link_type):
        result = resolve_edge_style(link_type)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_link_type_returns_default(self):
        result = resolve_edge_style("unknown_link_type_xyz")
        default = resolve_edge_style("default")
        assert result == default

    def test_fabric_is_thicker_than_uplink(self):
        """Fabric links should have strokeWidth=2, uplinks strokeWidth=1."""
        fabric = resolve_edge_style("fabric")
        assert "strokeWidth=2" in fabric

    def test_management_is_dashed(self):
        result = resolve_edge_style("management")
        assert "dashed=1" in result

    def test_wan_is_dashed(self):
        result = resolve_edge_style("wan")
        assert "dashed=1" in result

    def test_fabric_and_wan_are_different(self):
        assert resolve_edge_style("fabric") != resolve_edge_style("wan")


# ==============================================================================
# resolve_container_style
# ==============================================================================

class TestResolveContainerStyle:

    def test_minimal_returns_string(self):
        result = resolve_container_style("minimal")
        assert isinstance(result, str)
        assert "container=1" in result

    def test_dark_profile_returns_dark_style(self):
        result = resolve_container_style("dark")
        assert isinstance(result, str)
        assert "container=1" in result
        # Dark profile should have a dark fill
        assert "1a1a1a" in result or "fillColor" in result

    def test_unknown_profile_returns_default(self):
        result = resolve_container_style("unknown_profile")
        default = resolve_container_style("minimal")
        assert result == default

    def test_minimal_and_dark_are_different(self):
        assert resolve_container_style("minimal") != resolve_container_style("dark")

    def test_container_style_has_swimlane(self):
        result = resolve_container_style("minimal")
        assert "swimlane" in result


# ==============================================================================
# SUPPORTED_STYLE_PROFILES constant
# ==============================================================================

class TestSupportedStyleProfiles:

    def test_four_profiles_exist(self):
        assert len(SUPPORTED_STYLE_PROFILES) == 4

    def test_expected_profiles_present(self):
        for name in ("minimal", "enterprise", "dark", "vendor-neutral"):
            assert name in SUPPORTED_STYLE_PROFILES