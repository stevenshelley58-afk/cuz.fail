from scripts.wp6_extract import advisory_lock_key


def test_advisory_lock_key_is_stable_signed_63_bit() -> None:
    key = advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")

    assert key == advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")
    assert 0 <= key < 2**63
