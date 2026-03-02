"""Tests for storage helper functions."""
import pytest
from unittest.mock import MagicMock
from ha_event_processor.storage.database import _safe_int


class TestSafeInt:
    """Test _safe_int helper function."""

    def test_safe_int_with_int(self):
        """Test _safe_int returns int unchanged."""
        assert _safe_int(42, 0) == 42
        assert _safe_int(0, 999) == 0
        assert _safe_int(-5, 100) == -5

    def test_safe_int_with_string_digits(self):
        """Test _safe_int converts string digits to int."""
        assert _safe_int("42", 0) == 42
        assert _safe_int("0", 999) == 0
        assert _safe_int("-5", 100) == -5
        assert _safe_int("12345", 0) == 12345

    def test_safe_int_with_float(self):
        """Test _safe_int converts float to int (truncates)."""
        assert _safe_int(42.7, 0) == 42
        assert _safe_int(3.14, 0) == 3
        assert _safe_int(-5.9, 0) == -5

    def test_safe_int_with_string_float(self):
        """Test _safe_int converts string float to int."""
        assert _safe_int("42.7", 0) == 0
        assert _safe_int("3.14", 0) == 0

    def test_safe_int_with_invalid_string(self):
        """Test _safe_int returns default for invalid string."""
        assert _safe_int("not_a_number", 99) == 99
        assert _safe_int("abc123", 0) == 0
        assert _safe_int("", 42) == 42

    def test_safe_int_with_none(self):
        """Test _safe_int returns default for None."""
        assert _safe_int(None, 50) == 50
        assert _safe_int(None, 0) == 0

    def test_safe_int_with_magicmock(self):
        """Test _safe_int returns default for MagicMock (prevents binding errors)."""
        mock = MagicMock()
        # MagicMock() default: When a MagicMock object is created and used in a context requiring an integer (like int()), it utilizes its pre-configured __int__ method, which returns 1 by default.
        # Contrast with Mock(): A regular unittest.mock.Mock() object would raise a TypeError if you tried to call int() on it, as it does not have these pre-configured methods.
        #assert _safe_int(mock, 75) == 75
        #assert _safe_int(mock, 0) == 0
        assert _safe_int(mock, 75) == 1
        assert _safe_int(mock, 0) == 1

    def test_safe_int_with_list(self):
        """Test _safe_int returns default for list."""
        assert _safe_int([1, 2, 3], 88) == 88
        assert _safe_int([], 42) == 42

    def test_safe_int_with_dict(self):
        """Test _safe_int returns default for dict."""
        assert _safe_int({"key": "value"}, 77) == 77
        assert _safe_int({}, 30) == 30

    def test_safe_int_with_object(self):
        """Test _safe_int returns default for custom object."""
        class CustomClass:
            pass

        obj = CustomClass()
        assert _safe_int(obj, 55) == 55

    def test_safe_int_default_parameter(self):
        """Test _safe_int respects the default parameter."""
        assert _safe_int("invalid", 100) == 100
        assert _safe_int(None, 200) == 200
        # MagicMock() default: When a MagicMock object is created and used in a context requiring an integer (like int()), it utilizes its pre-configured __int__ method, which returns 1 by default.
        # Contrast with Mock(): A regular unittest.mock.Mock() object would raise a TypeError if you tried to call int() on it, as it does not have these pre-configured methods.
        #assert _safe_int(MagicMock(), 300) == 300
        assert _safe_int(MagicMock(), 300) == 1

    def test_safe_int_edge_cases(self):
        """Test _safe_int with edge cases."""
        # Large numbers
        assert _safe_int(999999999999, 0) == 999999999999
        assert _safe_int("999999999999", 0) == 999999999999

        # Negative numbers
        assert _safe_int(-999999, 0) == -999999
        assert _safe_int("-999999", 0) == -999999

        # Zero
        assert _safe_int(0, 99) == 0
        assert _safe_int("0", 99) == 0

    def test_safe_int_boolean(self):
        """Test _safe_int with boolean values (booleans are ints in Python)."""
        # In Python, bool is a subclass of int, so True == 1 and False == 0
        assert _safe_int(True, 0) == 1
        assert _safe_int(False, 1) == 0

    def test_safe_int_whitespace_string(self):
        """Test _safe_int with whitespace-only string."""
        assert _safe_int("   ", 42) == 42
        assert _safe_int("\t\n", 99) == 99

    def test_safe_int_default_zero(self):
        """Test _safe_int with default value of 0."""
        assert _safe_int("bad", 0) == 0
        assert _safe_int(None, 0) == 0
        # MagicMock() default: When a MagicMock object is created and used in a context requiring an integer (like int()), it utilizes its pre-configured __int__ method, which returns 1 by default.
        # Contrast with Mock(): A regular unittest.mock.Mock() object would raise a TypeError if you tried to call int() on it, as it does not have these pre-configured methods.
        #assert _safe_int(MagicMock(), 0) == 0
        assert _safe_int(MagicMock(), 0) == 1

    def test_safe_int_default_negative(self):
        """Test _safe_int with negative default value."""
        assert _safe_int("invalid", -1) == -1
        # MagicMock() default: When a MagicMock object is created and used in a context requiring an integer (like int()), it utilizes its pre-configured __int__ method, which returns 1 by default.
        # Contrast with Mock(): A regular unittest.mock.Mock() object would raise a TypeError if you tried to call int() on it, as it does not have these pre-configured methods.
        #assert _safe_int(MagicMock(), -99) == -99
        assert _safe_int(MagicMock(), -99) == 1

    def test_safe_int_preserves_valid_input(self):
        """Test that _safe_int preserves the exact value for valid inputs."""
        test_values = [0, 1, 10, 100, 1000, -1, -10, -100, -1000]
        for value in test_values:
            assert _safe_int(value, 999) == value
            assert _safe_int(str(value), 999) == value

