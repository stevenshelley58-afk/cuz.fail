from dataclasses import dataclass

from draftcheck.extraction.adjudication import model_family
from scripts.wp6_challenge import candidate_signature, endpoint_family, select_challenge_endpoints


@dataclass
class DummyEndpoint:
    name: str
    model: str

    def complete(self, system: str, prompt: str) -> str:
        return "{}"


def test_candidate_signature_matches_full_atom_shape() -> None:
    row = {
        "rule_key": "site_cover",
        "operator": "lte",
        "value_json": {"value": 50},
        "unit": "%",
        "condition_json": {"density_codes": ["R40", "R30"], "dwelling_type": "single_house"},
        "pathway": "deemed_to_comply",
    }

    assert candidate_signature(row) == (
        "site_cover",
        "lte",
        50.0,
        "%",
        ("R30", "R40"),
        "deemed_to_comply",
        "single_house",
    )


def test_select_challenge_endpoints_requires_different_family() -> None:
    minimax = DummyEndpoint("minimax", "MiniMax-M2")
    openai = DummyEndpoint("openai", "gpt-4o")

    selected = select_challenge_endpoints([minimax, openai], stored_family=model_family("minimax:MiniMax-M2"))

    assert selected == [openai, openai]
    assert endpoint_family(selected[0]) == "openai"


def test_select_challenge_endpoints_returns_empty_without_other_family() -> None:
    minimax = DummyEndpoint("minimax", "MiniMax-M2")

    assert select_challenge_endpoints([minimax], stored_family="minimax") == []
