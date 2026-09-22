"""Tell a real lossless file from one that was made out of an MP3."""

from .engine import analyse, score, localise, collect

__version__ = "0.1.0"
__all__ = ["analyse", "score", "localise", "collect", "__version__"]
