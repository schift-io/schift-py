"""Adapter registry — create adapters from config dicts."""

from __future__ import annotations

from schift.adapters.base import Adapter

_REGISTRY: dict[str, type[Adapter]] = {}


def _register_builtins():
    from schift.adapters.file import NpyAdapter
    _REGISTRY["npy"] = NpyAdapter

    _optional = {
        "pgvector": ("schift.adapters.pgvector", "PgVectorAdapter"),
        "qdrant": ("schift.adapters.qdrant", "QdrantAdapter"),
        "weaviate": ("schift.adapters.weaviate", "WeaviateAdapter"),
        "pinecone": ("schift.adapters.pinecone", "PineconeAdapter"),
        "milvus": ("schift.adapters.milvus", "MilvusAdapter"),
        "chroma": ("schift.adapters.chroma", "ChromaAdapter"),
        "elasticsearch": ("schift.adapters.elasticsearch", "ElasticsearchAdapter"),
        "redis": ("schift.adapters.redis", "RedisAdapter"),
        "mongodb": ("schift.adapters.mongodb", "MongoDBAdapter"),
    }
    import importlib
    for name, (module_path, class_name) in _optional.items():
        try:
            mod = importlib.import_module(module_path)
            _REGISTRY[name] = getattr(mod, class_name)
        except ImportError:
            pass


def get_adapter(config: dict) -> Adapter:
    """Create an adapter from a config dict.

    Example configs:
        {"type": "pgvector", "conninfo": "postgresql://...", "table": "docs"}
        {"type": "qdrant", "url": "http://localhost:6333", "collection": "docs"}
        {"type": "npy", "path": "embeddings.npy"}
    """
    if not _REGISTRY:
        _register_builtins()

    adapter_type = config.pop("type")
    if adapter_type not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown adapter: {adapter_type}. Available: {available}")

    return _REGISTRY[adapter_type](**config)


def list_adapters() -> list[str]:
    """List available adapter types."""
    if not _REGISTRY:
        _register_builtins()
    return list(_REGISTRY.keys())
