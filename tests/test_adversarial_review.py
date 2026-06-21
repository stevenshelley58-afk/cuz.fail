from scripts.adversarial_review import Finding, finding_for, load_prosecutor_findings, summarize


class FakeRows:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self._rows


class FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def execute(self, *_args, **_kwargs):
        self.statements.extend(str(arg) for arg in _args)
        return FakeRows(self.rows)


def test_finding_ids_are_deterministic() -> None:
    one = finding_for(1, "gap_hunter", "target:x", "claim", "quote", "major")
    two = finding_for(1, "gap_hunter", "target:x", "claim", "quote", "major")

    assert isinstance(one, Finding)
    assert one.id == two.id


def test_summarize_requires_two_clean_rounds_and_no_open_findings() -> None:
    report = summarize(
        FakeConn(
            [
                {"round": 1, "agent_role": "gap_hunter", "status": "rejected", "severity": "major", "count": 2},
                {"round": 2, "agent_role": "gap_hunter", "status": "rejected", "severity": "major", "count": 1},
            ]
        )
    )

    assert report["gate"]["passed"] is True


def test_summarize_fails_with_open_findings() -> None:
    report = summarize(
        FakeConn(
            [
                {"round": 1, "agent_role": "gap_hunter", "status": "rejected", "severity": "major", "count": 1},
                {"round": 2, "agent_role": "gap_hunter", "status": "open", "severity": "major", "count": 1},
            ]
        )
    )

    assert report["gate"]["passed"] is False


def test_prosecutor_findings_use_check_key_schema() -> None:
    conn = FakeConn(
        [
            {
                "id": "check-1",
                "status": "likely_fail",
                "check_key": "setback.primary_street",
                "trace": "{}",
            }
        ]
    )

    findings = load_prosecutor_findings(conn, 1, 10)

    assert "check_key" in conn.statements[0]
    assert "rule_key" not in conn.statements[0]
    assert findings[0].target == "check_result:check-1"
    assert "setback.primary_street" in findings[0].claim
