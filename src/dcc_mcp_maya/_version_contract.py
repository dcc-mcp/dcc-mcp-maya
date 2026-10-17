"""Dependency-free exact package versions used by the adapter.

This is NOT a requirement/specifier implementation. The only range operation is
this repository's stable ``>= minimum, < maximum`` contract. Exact versions
retain PEP 440 spelling/ordering (including aliases) so metadata provenance and
existing installer inputs do not lose epoch, pre/dev/post, or local identity.

Keep this leaf importable on Python 3.7 without importing Maya or native Core.
Core's public SemVer currently ignores prereleases and cannot replace it. Tests
compare normalization, ordering, and the fixed range against the build/dev-only
``packaging`` oracle; no third-party implementation is copied or vendored here.
"""

from __future__ import annotations

import re
from functools import total_ordering

# Full-match the standardized exact-version grammar, never extract a numeric
# prefix from arbitrary metadata. Separators/aliases are normalized below.
_EXACT = re.compile(
    r"v?(?:(?P<epoch>[0-9]+)!)?(?P<release>[0-9]+(?:\.[0-9]+)*)"
    r"(?:[-_.]?(?P<pre>alpha|beta|preview|pre|rc|a|b|c)[-_.]?(?P<pre_n>[0-9]+)?)?"
    r"(?:(?:-(?P<post_implicit>[0-9]+))|(?:[-_.]?(?P<post>post|rev|r)[-_.]?(?P<post_n>[0-9]+)?))?"
    r"(?:[-_.]?(?P<dev>dev)[-_.]?(?P<dev_n>[0-9]+)?)?"
    r"(?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?",
    re.IGNORECASE | re.ASCII,
)
_PRE_LABEL = {"alpha": "a", "a": "a", "beta": "b", "b": "b", "c": "rc", "pre": "rc", "preview": "rc", "rc": "rc"}


class InvalidVersion(ValueError):
    """The complete input is not an exact package version."""


@total_ordering
class Version:
    """An exact version; equality preserves epoch/local provenance identity."""

    def __init__(self, value):
        match = _EXACT.fullmatch(value.strip()) if isinstance(value, str) else None
        if match is None:
            raise InvalidVersion("Invalid version: %r" % value)
        fields = match.groupdict()
        self.epoch = int(fields["epoch"] or 0)
        self.release = tuple(int(part) for part in fields["release"].split("."))
        self.pre = (_PRE_LABEL[fields["pre"].lower()], int(fields["pre_n"] or 0)) if fields["pre"] else None
        self.post = (
            int(fields["post_implicit"] or fields["post_n"] or 0)
            if fields["post"] or fields["post_implicit"] is not None
            else None
        )
        self.dev = int(fields["dev_n"] or 0) if fields["dev"] else None
        self.local = (
            tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"[-_.]", fields["local"]))
            if fields["local"]
            else ()
        )
        release = list(self.release)
        while release and release[-1] == 0:
            release.pop()
        # A bare development release precedes even alpha. A final release has
        # no prerelease marker and follows all prereleases of that release.
        pre = (
            (0, ("a", "b", "rc").index(self.pre[0]), self.pre[1])
            if self.pre
            else ((-1,) if self.dev is not None and self.post is None else (1,))
        )
        self._key = (
            self.epoch,
            tuple(release),
            pre,
            (0,) if self.post is None else (1, self.post),
            (1,) if self.dev is None else (0, self.dev),
            tuple((1, part) if isinstance(part, int) else (0, part) for part in self.local),
        )

    @property
    def is_prerelease(self):
        return self.pre is not None or self.dev is not None

    def __str__(self):
        value = ("%d!" % self.epoch if self.epoch else "") + ".".join(map(str, self.release))
        if self.pre:
            value += "%s%d" % self.pre
        if self.post is not None:
            value += ".post%d" % self.post
        if self.dev is not None:
            value += ".dev%d" % self.dev
        if self.local:
            value += "+" + ".".join(map(str, self.local))
        return value

    def __eq__(self, other):
        return self._key == other._key if isinstance(other, Version) else NotImplemented

    def __lt__(self, other):
        return self._key < other._key if isinstance(other, Version) else NotImplemented

    def __hash__(self):
        return hash(self._key)


class StableReleaseRange:
    """Only inclusive/exclusive stable bounds, with explicit prerelease policy.

    The module ZIP's prior packaging 24.0 behavior excluded *all* pre/dev
    releases. Preserve that policy explicitly, rather than depending on the
    ambient packaging version's changing automatic prerelease behavior.
    """

    def __init__(self, minimum, maximum):
        self.minimum, self.maximum = Version(minimum), Version(maximum)
        if any(version.is_prerelease or version.local for version in (self.minimum, self.maximum)):
            raise ValueError("Core range bounds must be stable public versions")
        if not self.minimum < self.maximum:
            raise ValueError("Core range must have increasing bounds")

    def __contains__(self, value):
        try:
            version = value if isinstance(value, Version) else Version(value)
        except InvalidVersion:
            return False
        return not version.is_prerelease and self.minimum <= version < self.maximum

    def __str__(self):
        return ">=%s,<%s" % (self.minimum, self.maximum)


def canonicalize_name(value):
    """Normalize a distribution identity, not an import-module name."""
    return re.sub(r"[-_.]+", "-", value).lower()
