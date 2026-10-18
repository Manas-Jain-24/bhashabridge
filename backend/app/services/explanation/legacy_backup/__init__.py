"""
BhashaBridge - Legacy Explanation Engine Backup
Preserved original baseline implementation for safe fallback.
"""
from .engine_legacy import HybridExplanationEngine as LegacyExplanationEngine, explanation_engine as legacy_explanation_engine

__all__ = ["LegacyExplanationEngine", "legacy_explanation_engine"]
