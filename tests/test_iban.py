from core.iban import build_de_iban, format_iban, mask_iban, normalize_iban, validate_iban


def test_build_produces_valid_iban():
    iban = build_de_iban("01234500", 1000001)
    assert iban.startswith("DE")
    assert len(iban) == 22
    assert validate_iban(iban)


def test_validate_accepts_spaces_and_lowercase():
    iban = build_de_iban("01234500", 42)
    assert validate_iban(format_iban(iban).lower())


def test_validate_rejects_wrong_check_digits():
    iban = build_de_iban("01234500", 1000001)
    wrong = "DE%02d%s" % ((int(iban[2:4]) + 1) % 100, iban[4:])
    assert not validate_iban(wrong)


def test_validate_rejects_empty_and_malformed():
    assert not validate_iban("")
    assert not validate_iban(None)
    assert not validate_iban("keine iban")


def test_format_and_mask():
    iban = build_de_iban("01234500", 7)
    assert format_iban(iban).count(" ") == 5
    assert normalize_iban(format_iban(iban)) == iban
    masked = mask_iban(iban)
    assert masked.startswith(iban[:4]) and masked.endswith(iban[-4:]) and "*" in masked
