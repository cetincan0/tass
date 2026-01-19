from src.tools.edit_file import fuzzy_match


file_contents = """def fib(n):
    '''Return the nth Fibonacci number (iterative).'''
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


if __name__ == "__main__":
    # Print first 10 Fibonacci numbers
    for i in range(11):
        print(f"fib({i}) = {fib(i)}")"""


def test_fuzzy():
    edit_find = "    return b\n\n\n\nif __name__ == \"__main__\":"
    lines = file_contents.split("\n")
    assert fuzzy_match(edit_find, lines) == (10, 13)

    edit_find = "def fib(n):\n\n    '''Return the nth Fibonacci number (iterative).'''\n\n    if n <= 0:\n\n        return 0\n\n    if n == 1:\n\n        return 1\n\n    a, b = 0, 1\n\n    for _ in range(2, n + 1):\n\n        a, b = b, a + b\n\n    return b"
    assert fuzzy_match(edit_find, lines) == (1, 10)
