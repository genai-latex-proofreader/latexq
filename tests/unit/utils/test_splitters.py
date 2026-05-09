from lq.utils.splitters import split_leading


# --- test split_leading ---


def test_split_leading_returns_matching_prefix_and_remainder():
    assert split_leading([0, 0, 1, 0], lambda value: value == 0) == (
        [0, 0],
        [1, 0],
    )


def test_split_leading_returns_empty_prefix_when_first_item_does_not_match():
    assert split_leading([1, 0, 0], lambda value: value == 0) == ([], [1, 0, 0])


def test_split_leading_returns_all_items_when_all_match():
    assert split_leading(["", "  ", "\n"], lambda line: line.strip() == "") == (
        ["", "  ", "\n"],
        [],
    )


def test_split_leading_accepts_sequence_input_and_returns_lists():
    assert split_leading((0, 0, 1), lambda value: value == 0) == ([0, 0], [1])
