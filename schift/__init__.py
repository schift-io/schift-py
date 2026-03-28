from schift.schift_client import Schift
from schift.projection import Projection
from schift.migrate import migrate
# Kept for backwards compatibility — use Schift instead.
from schift.client import Client, BenchReport

__version__ = "0.1.0"
__all__ = ["Schift", "Projection", "migrate", "Client", "BenchReport"]
