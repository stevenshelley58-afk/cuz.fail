from __future__ import annotations

from scripts import extract_rcodes_v3


class _Page:
    def __init__(self, tables):
        self._tables = tables

    def extract_tables(self, _settings):
        return self._tables


class _Pdf:
    def __init__(self, tables):
        self.pages = [_Page(tables)]


def _matrix(value: str):
    header = ["height", "10"] + [""] * 13
    return [
        header,
        header,
        ["", ""] + [""] * 13,
        ["3.5 or less", value] + [""] * 13,
    ]


def test_parse_table_2x_only_returns_requested_matrix(monkeypatch) -> None:
    monkeypatch.setattr(extract_rcodes_v3, "find_page", lambda *_args: 0)
    pdf = _Pdf([_matrix("1.0"), _matrix("2.0")])

    candidates, warnings = extract_rcodes_v3.parse_table_2x(
        pdf,
        "Part B",
        "source-version",
        {"Table 2a": "clause-a", "Table 2b": "clause-b"},
        requested_tables={"Table 2a"},
    )

    assert not warnings
    assert candidates
    assert {candidate["table_reference"] for candidate in candidates} == {"Table 2a"}
    assert {candidate["clause_id"] for candidate in candidates} == {"clause-a"}
