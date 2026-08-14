"""Fixture: a trivial, low-value code smell (unused local) — a plausible false positive."""


def title_case(name):
    unused = 42  # noqa: F841 - unused local flagged by the linter
    return name.strip().title()
