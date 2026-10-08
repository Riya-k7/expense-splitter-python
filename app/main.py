from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import cache, db
from .settle import SettleError, settle, split_evenly, to_paise

app = FastAPI(title="expense-splitter")


@app.get("/health")
def health():
    out = {"status": "ok", "postgres": False, "redis": False}
    try:
        db.query("SELECT 1")
        out["postgres"] = True
    except Exception as e:
        out["pg_error"] = str(e)
    try:
        cache.client().ping()
        out["redis"] = True
    except Exception as e:
        out["redis_error"] = str(e)
    return out if out["postgres"] and out["redis"] else JSONResponse(out, status_code=503)


@app.get("/groups/{gid}")
def group(gid: int):
    members = db.query("SELECT id, name FROM members WHERE group_id=%s ORDER BY id", (gid,))
    if not members:
        raise HTTPException(404, "no such group")
    bills = db.query(
        "SELECT b.id, b.payer_id, b.amount_paise, b.note,"
        " json_agg(json_build_object('member_id', s.member_id, 'paise', s.paise)) AS shares"
        " FROM bills b JOIN shares s ON s.bill_id=b.id"
        " WHERE b.group_id=%s GROUP BY b.id ORDER BY b.id", (gid,))
    return {"group_id": gid, "members": members, "bills": bills}


@app.post("/groups/{gid}/bills", status_code=201)
def add_bill(gid: int, payload: dict = Body(...)):
    try:
        amount = to_paise(payload.get("amount"))
    except SettleError as e:
        raise HTTPException(400, str(e))

    payer = payload.get("payer_id")
    members = [m["id"] for m in
               db.query("SELECT id FROM members WHERE group_id=%s", (gid,))]
    if payer not in members:
        raise HTTPException(400, "payer is not in this group")

    raw = payload.get("shares")
    if raw:
        shares = {int(k): int(v) for k, v in raw.items()}
        if sum(shares.values()) != amount:
            raise HTTPException(400, "shares must add up to the bill amount")
    else:
        parts = split_evenly(amount, len(members))
        shares = dict(zip(members, parts))

    bill = db.one("INSERT INTO bills (group_id, payer_id, amount_paise, note)"
                  " VALUES (%s,%s,%s,%s) RETURNING id",
                  (gid, payer, amount, str(payload.get("note", ""))[:200]))
    with db.connect() as conn, conn.cursor() as cur:
        for mid, paise in shares.items():
            cur.execute("INSERT INTO shares (bill_id, member_id, paise) VALUES (%s,%s,%s)",
                        (bill["id"], mid, paise))
    cache.drop(f"settle:{gid}")
    return {"bill_id": bill["id"], "amount_paise": amount, "shares": shares}


@app.get("/groups/{gid}/settlement")
def settlement(gid: int):
    hit = cache.get_json(f"settle:{gid}")
    if hit:
        return {**hit, "cached": True}
    rows = db.query(
        "SELECT b.id, b.payer_id, b.amount_paise,"
        " json_object_agg(s.member_id, s.paise) AS shares"
        " FROM bills b JOIN shares s ON s.bill_id=b.id"
        " WHERE b.group_id=%s GROUP BY b.id", (gid,))
    if not rows:
        return {"group_id": gid, "payments": [], "cached": False}
    bills = [{"payer": r["payer_id"], "amount": r["amount_paise"],
              "shares": {int(k): v for k, v in r["shares"].items()}} for r in rows]
    try:
        payments = settle(bills)
    except SettleError as e:
        raise HTTPException(500, str(e))
    names = {m["id"]: m["name"] for m in
             db.query("SELECT id, name FROM members WHERE group_id=%s", (gid,))}
    out = {"group_id": gid, "payments": [
        {"from": names.get(p["from"], p["from"]), "to": names.get(p["to"], p["to"]),
         "rupees": round(p["paise"] / 100, 2)} for p in payments]}
    cache.set_json(f"settle:{gid}", out, ttl=300)
    return {**out, "cached": False}
