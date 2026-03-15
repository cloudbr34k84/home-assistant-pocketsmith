"""Shared helpers for the PocketSmith integration."""


def non_transfer_budget_packages(budget: list) -> list:
    """Return budget packages that are not transfers."""
    return [pkg for pkg in budget if not pkg.get("is_transfer")]
