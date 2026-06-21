from scripts import resolve_manifest_urls
from scripts.resolve_manifest_urls import parse_index_page, resolve_rows


class FakeRows:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self._rows


class FakeConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []
        self.params = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        self.params.append(params or {})
        return FakeRows(self.rows)


class FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    def connect(self):
        return self.conn

    def begin(self):
        return self.conn


def test_parse_index_page_extracts_official_pdf() -> None:
    html = """
    <article><table><tbody>
      <tr>
        <td><a href="law_a1.html&amp;view=consolidated">Aboriginal Affairs Planning Authority Act 1972</a></td>
        <td>024 of 1972</td>
        <td><a href="RedirectURL?OpenAgent&amp;query=mrdoc_49436.pdf"><span>Official Version</span></a></td>
      </tr>
    </tbody></table></article>
    """

    entries = parse_index_page(
        html,
        collection="acts",
        page_url="https://www.legislation.wa.gov.au/legislation/statutes.nsf/actsif_a.html",
    )

    assert len(entries) == 1
    assert entries[0].title == "Aboriginal Affairs Planning Authority Act 1972"
    assert entries[0].pdf_url.endswith("RedirectURL?OpenAgent&query=mrdoc_49436.pdf")


def test_resolve_rows_matches_by_category_and_exact_title() -> None:
    html = """
    <article><table><tbody>
      <tr>
        <td><a href="law_s1.html&amp;view=consolidated">Planning Example Regulations 2024</a></td>
        <td>Regulations</td>
        <td><a href="RedirectURL?OpenAgent&amp;query=mrdoc_1.pdf"><span>Official Version</span></a></td>
      </tr>
    </tbody></table></article>
    """
    entries = parse_index_page(
        html,
        collection="subsidiary",
        page_url="https://www.legislation.wa.gov.au/legislation/statutes.nsf/subsif_p.html",
    )
    resolved, unresolved = resolve_rows(
        [
            {
                "id": "row-1",
                "instrument_name": "Planning Example Regulations 2024",
                "category": "regulations",
                "issuing_authority": "Government of Western Australia",
            },
            {
                "id": "row-2",
                "instrument_name": "Missing Act 1900",
                "category": "act",
                "issuing_authority": "Government of Western Australia",
            },
        ],
        {"acts": {}, "subsidiary": {entries[0].title.casefold(): entries[0]}},
    )

    assert [row["id"] for row in resolved] == ["row-1"]
    assert [row["id"] for row in unresolved] == ["row-2"]


def test_pending_rows_scans_blocked_and_pending(monkeypatch) -> None:
    conn = FakeConn(
        [
            {
                "id": "row-1",
                "instrument_name": "Planning Act 1900",
                "category": "act",
                "issuing_authority": "Government of Western Australia",
                "status": "blocked",
            }
        ]
    )
    monkeypatch.setattr(resolve_manifest_urls, "create_engine", lambda _url: FakeEngine(conn))

    rows = resolve_manifest_urls.pending_rows("postgresql://example")

    assert rows[0]["status"] == "blocked"
    assert "status = ANY(:statuses)" in conn.statements[0]
    assert conn.params[0]["statuses"] == ["pending", "blocked"]


def test_apply_resolutions_returns_blocked_rows_to_pending(monkeypatch) -> None:
    conn = FakeConn()
    monkeypatch.setattr(resolve_manifest_urls, "create_engine", lambda _url: FakeEngine(conn))

    resolve_manifest_urls.apply_resolutions(
        "postgresql://example",
        [{"id": "row-1", "canonical_url": "https://example.test/a.pdf", "title_url": "https://example.test/a"}],
    )

    assert "status = 'pending'" in conn.statements[0]
    assert "status IN ('pending', 'blocked')" in conn.statements[0]
