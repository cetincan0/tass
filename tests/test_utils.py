import pytest

from src.utils import is_read_only_command


@pytest.mark.parametrize(
    "command,expected",
    [
        ("ls", True),
        ("cat file.txt", True),
        ("ls | grep py", True),
        ("cat file.txt > out.txt", False),
        ("echo '<false_negative>'", False),
        ("find . -name \"*.py\"", True),
        ("sed 's/foo/bar/' file.txt", True),
        ("wc -l file.txt", True),
        ("unknowncmd", False),
        ("ls | grep py | wc -l", True),
        ("ls | grep py | rm", False),
    ],
)
def test_is_read_only_command(command, expected):
    assert is_read_only_command(command) == expected
