from app.lib.logger import get_logger

logger = get_logger(__name__)


class FeatureFlag:
    """Simple in-memory feature flag system.

    Falls back to default if no override is set.
    In production, this would read from system_configs/Redis.
    """

    _flags: dict[str, bool] = {
        "executor.android.enabled": False,
        "executor.ios.enabled": False,
        "analysis.llm_fallback": True,
        "extraction.strategy_v2": False,
    }

    @classmethod
    def is_enabled(cls, flag_name: str, default: bool = False) -> bool:
        return cls._flags.get(flag_name, default)

    @classmethod
    def set_flag(cls, flag_name: str, enabled: bool):
        cls._flags[flag_name] = enabled
        logger.info("Feature flag %s set to %s", flag_name, enabled)

    @classmethod
    def reset(cls):
        cls._flags.clear()
