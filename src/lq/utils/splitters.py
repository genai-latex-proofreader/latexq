from collections.abc import Callable, Sequence
from typing import TypeVar


A = TypeVar("A")


def split_leading(
    items: Sequence[A],
    keep_in_prefix: Callable[[A], bool],
) -> tuple[list[A], list[A]]:
    """Split off the longest leading prefix that matches a predicate."""
    split_index = 0
    for item in items:
        if not keep_in_prefix(item):
            break
        split_index += 1

    return list(items[:split_index]), list(items[split_index:])
