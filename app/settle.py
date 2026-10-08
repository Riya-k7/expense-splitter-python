"""Pure settlement maths. Money is handled in paise (integers) throughout -
floats cannot represent 0.1 exactly and a settlement that is 0.01 out is a bug.
"""


class SettleError(ValueError):
    pass


def to_paise(rupees):
    """Convert to integer paise, rejecting anything that is not money."""
    try:
        v = round(float(rupees) * 100)
    except (TypeError, ValueError):
        raise SettleError(f"{rupees!r} is not an amount")
    if v <= 0:
        raise SettleError("an amount must be positive")
    return v


def split_evenly(total_paise, n):
    """Split an amount n ways so the parts add up EXACTLY to the total.

    100 rupees between 3 people is 33.34 + 33.33 + 33.33, not 33.33 x 3.
    The extra paise go to the earliest shares, deterministically.
    """
    if n <= 0:
        raise SettleError("cannot split between nobody")
    base, extra = divmod(total_paise, n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def balances(bills):
    """Net position per person. Positive means they are owed money.

    Each bill is {"payer": id, "amount": paise, "shares": {id: paise}}.
    """
    net = {}
    for b in bills:
        shares = b["shares"]
        if sum(shares.values()) != b["amount"]:
            raise SettleError(
                f"shares total {sum(shares.values())} but the bill is {b['amount']}")
        net[b["payer"]] = net.get(b["payer"], 0) + b["amount"]
        for person, owed in shares.items():
            net[person] = net.get(person, 0) - owed
    return net


def settle(bills):
    """Reduce the balances to the fewest payments.

    Greedy: repeatedly match the largest debtor with the largest creditor.
    Not provably minimal in every case, but close, and easy to defend.
    """
    net = balances(bills)
    if sum(net.values()) != 0:
        raise SettleError("balances do not net to zero - a bill is malformed")

    debtors = sorted(((p, -v) for p, v in net.items() if v < 0),
                     key=lambda x: (-x[1], str(x[0])))
    creditors = sorted(((p, v) for p, v in net.items() if v > 0),
                       key=lambda x: (-x[1], str(x[0])))

    payments = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        (d, owe), (c, due) = debtors[i], creditors[j]
        amount = min(owe, due)
        payments.append({"from": d, "to": c, "paise": amount})
        owe -= amount
        due -= amount
        debtors[i] = (d, owe)
        creditors[j] = (c, due)
        if owe == 0:
            i += 1
        if due == 0:
            j += 1
    return payments


def total_moved(payments):
    return sum(p["paise"] for p in payments)
