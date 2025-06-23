"""Basic unit tests to ensure CI pipeline works."""

import pytest


def test_basic_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5


def test_string_operations():
    """Test basic string operations."""
    assert "hello".upper() == "HELLO"
    assert "WORLD".lower() == "world"
    assert "test".replace("t", "b") == "besb"


def test_list_operations():
    """Test basic list operations."""
    test_list = [1, 2, 3]
    assert len(test_list) == 3
    assert test_list[0] == 1
    assert 2 in test_list


def test_dict_operations():
    """Test basic dictionary operations."""
    test_dict = {"key": "value", "number": 42}
    assert test_dict["key"] == "value"
    assert test_dict.get("number") == 42
    assert "key" in test_dict


@pytest.mark.parametrize(
    "input_val,expected",
    [
        (1, 2),
        (2, 4),
        (3, 6),
        (0, 0),
    ],
)
def test_double_function(input_val, expected):
    """Test a simple doubling function with parametrized inputs."""

    def double(x):
        return x * 2

    assert double(input_val) == expected


def test_exception_handling():
    """Test exception handling."""
    with pytest.raises(ZeroDivisionError):
        1 / 0

    with pytest.raises(KeyError):
        test_dict = {"a": 1}
        test_dict["b"]  # This will raise KeyError


class TestBasicClass:
    """Test class for basic functionality."""

    def test_class_method(self):
        """Test a basic class method."""
        assert True

    def test_setup_and_teardown(self):
        """Test setup and teardown functionality."""
        # This test ensures pytest can handle class-based tests
        test_data = {"initialized": True}
        assert test_data["initialized"] is True
