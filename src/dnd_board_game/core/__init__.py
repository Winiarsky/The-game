"""Shared primitives for the new game runtime."""

from .migrations import MigrationError, MigrationRegistry

__all__ = ["MigrationError", "MigrationRegistry"]
