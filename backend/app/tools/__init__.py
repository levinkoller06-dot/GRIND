# Beim Import registrieren sich alle Tools im REGISTRY.
from app.tools import essen, gym, kalender, mails, noten  # noqa: F401
from app.tools.base import REGISTRY, Tool, ToolContext

__all__ = ["REGISTRY", "Tool", "ToolContext"]
