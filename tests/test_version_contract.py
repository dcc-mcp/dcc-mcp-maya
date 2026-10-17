"""Exact-version semantics; packaging is a build/dev test oracle, never runtime."""

from __future__ import annotations

import itertools
import runpy
import unittest
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name as oracle_name
from packaging.version import InvalidVersion as OracleInvalidVersion
from packaging.version import Version as OracleVersion

# Load the leaf directly: this suite must not require Maya or a native Core wheel.
CONTRACT = runpy.run_path(str(Path(__file__).resolve().parents[1] / "src/dcc_mcp_maya/_version_contract.py"))
Version = CONTRACT["Version"]
InvalidVersion = CONTRACT["InvalidVersion"]
StableReleaseRange = CONTRACT["StableReleaseRange"]


def public_inputs():
    """Published-release spellings plus the standardized public input grammar."""
    # Real Core/adapter release identities and common PyPI spellings. No network
    # or ambient installed project metadata is needed for a reproducible oracle.
    yield from ("0.20.0", "0.20.42", "0.20.44", "0.9.31", "0.9.35", "0.9.36", "1.0", "1.0.0.0")
    for epoch, release, suffix, local in itertools.product(
        ("", "0!", "2!"),
        ("0.20.0", "00.020.001", "0.21.0"),
        (
            "",
            "a",
            "alpha-01",
            "b2",
            "beta_02",
            "c3",
            "pre3",
            "preview3",
            "rc3",
            ".dev",
            "-dev_2",
            ".post",
            "-1",
            "rev2",
            "r_02",
            "rc1.post2.dev3",
            ".post1.dev2",
        ),
        ("", "+local", "+AbC-01_def", "+1.abc", "+abc.1", "+1.2"),
    ):
        yield epoch + release + suffix + local
    yield from (" v01.002RC_3 ", "1.0-0", "1.0post0", "1.0rc", "1.0a0.dev0", "1.0.post0.dev0")


class TestExactVersionContract(unittest.TestCase):
    def test_normalization_and_full_order_match_oracle(self):
        values = list(public_inputs())
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(str(Version(value)), str(OracleVersion(value)))
        self.assertEqual(sorted(values, key=Version), sorted(values, key=OracleVersion))
        # Equal normalized precedence must also preserve provenance equality,
        # including trailing zeros, aliases, epochs and local numeric segments.
        for left, right in zip(sorted(values, key=OracleVersion), sorted(values, key=OracleVersion)[1:]):
            self.assertEqual(Version(left) == Version(right), OracleVersion(left) == OracleVersion(right))

    def test_identity_does_not_discard_local_or_epoch(self):
        equal = (
            ("0.20", "0.20.0.0"),
            ("0!0.20.00", "0.20.0"),
            ("0.20.0+ABC-001", "0.20.0+abc.1"),
            ("0.20.0-1", "0.20.0.post1"),
        )
        for left, right in equal:
            self.assertEqual(Version(left), Version(right))
            self.assertEqual(hash(Version(left)), hash(Version(right)))
        for value in ("0.20.0+local", "1!0.20.0", "0.20.0rc1", "0.20.0.post1"):
            self.assertNotEqual(Version(value), Version("0.20.0"))

    def test_invalid_inputs_fail_closed(self):
        invalid = (
            "",
            " ",
            "garbage 0.20.0",
            "0.20.0 garbage",
            "0.20.0\ngarbage",
            "0..20.0",
            "0.20.",
            "0.20.0+",
            "0.20.0+abc..def",
            "0.20.0+abc!def",
            "1!!0.20.0",
            "0.20.0dev1rc1",
            "0.20.0post1post2",
            "1.0~rc1",
            "1.0.0.unknown",
            "0.２０.0",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(OracleInvalidVersion):
                    OracleVersion(value)
                with self.assertRaises(InvalidVersion):
                    Version(value)
        for value in (None, 123, {}, []):
            with self.assertRaises(InvalidVersion):
                Version(value)

    def test_non_ascii_local_lookalikes_fail_closed(self):
        # PEP 440 identifiers are ASCII. Packaging 24.0 accidentally accepted
        # these through Unicode IGNORECASE; 26.3 rejects them. Do not inherit
        # the older parser's out-of-spec acceptance into provenance checks.
        for value in ("1.0+K", "1.0+ı", "1.0+İ", "1.0+ſ"):
            with self.subTest(value=value), self.assertRaises(InvalidVersion):
                Version(value)

    def test_stable_range_matches_published_zip_policy_explicitly(self):
        supported = StableReleaseRange("0.20.0", "0.21.0")
        oracle = SpecifierSet(">=0.20.0,<0.21.0")
        for value in public_inputs():
            # Explicit False pins the published packaging 24.0 policy even when
            # newer oracle releases auto-admit interior prereleases by default.
            self.assertEqual(value in supported, oracle.contains(value, prereleases=False), value)
        for value in ("0.20.0rc1", "0.20.1rc1", "0.20.1.dev1", "0.21.0rc1", "0.21.0.dev1"):
            self.assertNotIn(value, supported)
        for value in ("0.20.0", "0.20.0.0", "v0.20.0", "0.20.0-1", "0.20.0+local"):
            self.assertIn(value, supported)
        self.assertNotIn("0.20.0garbage", supported)

    def test_range_is_deliberately_not_a_general_specifier(self):
        for minimum, maximum in (("0.20.0rc1", "0.21.0"), ("0.20.0", "0.21.0+local"), ("0.21", "0.20")):
            with self.assertRaises(ValueError):
                StableReleaseRange(minimum, maximum)

    def test_headless_floor_preserves_exact_ordering(self):
        floor = Version("0.19.64")
        for value in (
            "0.19.63",
            "0.19.64rc1",
            "0.19.64.dev1",
            "0.19.64",
            "0.19.64.post1",
            "0.19.64+local",
            "0.19.65rc1",
            "1!0.0",
            "0!0.19.64",
        ):
            self.assertEqual(Version(value) >= floor, OracleVersion(value) >= OracleVersion("0.19.64"))

    def test_distribution_identity_normalization(self):
        for value in ("dcc-mcp-core", "DCC_MCP.Core", "DCC___mcp...core", "other"):
            self.assertEqual(CONTRACT["canonicalize_name"](value), oracle_name(value))


if __name__ == "__main__":
    unittest.main()
