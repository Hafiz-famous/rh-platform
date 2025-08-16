
import hmac, hashlib, time
from flask import current_app

def sign_token(payload: str, ttl_seconds: int = 120) -> str:
    secret = current_app.config["SECRET_KEY"].encode()
    ts = str(int(time.time()))
    base = f"{payload}|ts:{ts}"
    sig = hmac.new(secret, base.encode(), hashlib.sha256).hexdigest()
    return f"{base}|sig:{sig}|ttl:{ttl_seconds}"

def verify_token(token: str) -> bool:
    secret = current_app.config["SECRET_KEY"].encode()
    parts = dict(kv.split(":", 1) for kv in token.split("|") if ":" in kv)
    required = ("ts", "sig", "ttl")
    if not all(k in parts for k in required):
        return False
    base = token.split("|sig:")[0]
    expected = hmac.new(secret, base.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts["sig"]):
        return False
    now = int(time.time())
    ts = int(parts["ts"]); ttl = int(parts["ttl"])
    return (now - ts) <= ttl
