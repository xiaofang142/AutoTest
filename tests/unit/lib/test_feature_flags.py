import pytest
from app.lib.feature_flags import FeatureFlag


class TestFeatureFlag:
    def setup_method(self):
        FeatureFlag.reset()

    def test_default_disabled(self):
        assert FeatureFlag.is_enabled("nonexistent") is False

    def test_default_enabled(self):
        assert FeatureFlag.is_enabled("nonexistent", True) is True

    def test_set_and_check(self):
        FeatureFlag.set_flag("my_feature", True)
        assert FeatureFlag.is_enabled("my_feature") is True

    def test_set_disabled(self):
        FeatureFlag.set_flag("my_feature", True)
        FeatureFlag.set_flag("my_feature", False)
        assert FeatureFlag.is_enabled("my_feature") is False

    def test_reset(self):
        FeatureFlag.set_flag("flag_a", True)
        FeatureFlag.reset()
        assert FeatureFlag.is_enabled("flag_a") is False
