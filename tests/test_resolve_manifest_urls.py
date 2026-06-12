from scripts.resolve_manifest_urls import parse_index_page, resolve_rows


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
