import pytest
from app import settle as settle_mod
from app.settle import to_paise, split_evenly, balances, settle, total_moved, SettleError

def test_to_paise_success():
    assert to_paise(10.50) == 1050
    assert to_paise("100") == 10000

def test_to_paise_errors():
    with pytest.raises(SettleError, match="is not an amount"):
        to_paise("invalid_money")
    with pytest.raises(SettleError, match="an amount must be positive"):
        to_paise(-50)
    with pytest.raises(SettleError, match="an amount must be positive"):
        to_paise(0)

def test_split_evenly():
    # 100 paise split 3 ways -> 34, 33, 33 (earliest indices get the extra remainder)
    assert split_evenly(100, 3) == [34, 33, 33]
    with pytest.raises(SettleError, match="cannot split between nobody"):
        split_evenly(100, 0)

def test_balances_malformed_bill():
    # Shares do not add up to the total bill amount
    malformed_bill = [{"payer": "1", "amount": 1000, "shares": {"1": 400, "2": 400}}]
    with pytest.raises(SettleError, match="shares total 800 but the bill is 1000"):
        balances(malformed_bill)

def test_settle_successful():
    # User 1 paid 1200 paise, split equally among 1, 2, and 3 (400 each)
    bills = [
        {
            "payer": "1",
            "amount": 1200,
            "shares": {"1": 400, "2": 400, "3": 400}
        }
    ]
    payments = settle(bills)
    assert len(payments) == 2
    assert {"from": "2", "to": "1", "paise": 400} in payments
    assert {"from": "3", "to": "1", "paise": 400} in payments
    assert total_moved(payments) == 800

def test_settle_malformed_net_balances(monkeypatch):
    # Dynamically force balances to return an asymmetric net dictionary that does not equal 0
    # This directly triggers line 58: "balances do not net to zero - a bill is malformed"
    monkeypatch.setattr(settle_mod, "balances", lambda bills: {"1": 500, "2": -200})
    
    with pytest.raises(SettleError, match="balances do not net to zero"):
        settle([])


