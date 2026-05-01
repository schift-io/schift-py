from schift.schift_client import Schift
from schift.projection import Projection
from schift.migrate import migrate
from schift.openai_compat import openai_client
# Kept for backwards compatibility — use Schift instead.
from schift.client import Client, BenchReport

__version__ = "0.6.0"
__all__ = [
    "Schift", "Projection", "migrate",
    "openai_client",
    "Client", "BenchReport",
]
