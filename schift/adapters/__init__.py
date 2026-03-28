"""Schift adapters — Source/Sink pattern for any vector store."""

from schift.adapters.base import Adapter
from schift.adapters.registry import get_adapter, list_adapters

__all__ = ["Adapter", "get_adapter", "list_adapters"]
