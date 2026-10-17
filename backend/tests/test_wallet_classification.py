from app.services.wallet_cluster import classify_wallet, extract_wallets_from_text


def test_extracts_and_normalises_eth_wallet():
    address = "0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD"
    found = extract_wallets_from_text(f"pay {address}")
    assert found["eth"] == [address.lower()]


def test_service_wallet_classification_is_explicit():
    address = "0x0000000000000000000000000000000000000000"
    result = classify_wallet(address, {address: "service"})
    assert result["valid"] is True
    assert result["wallet_class"] == "service"
