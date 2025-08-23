# app/services/qr_sign.py
import hmac, time, hashlib, urllib.parse
from flask import current_app

def sign_url(path_with_query: str, ttl=60):
    secret = current_app.config["SECRET_KEY"].encode()
    exp = int(time.time()) + ttl
    payload = f"{path_with_query}|{exp}".encode()
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return f"{path_with_query}&exp={exp}&sig={sig}"

def verify_signature(path_with_query: str, exp: int, sig: str) -> bool:
    if int(time.time()) > int(exp):
        return False
    secret = current_app.config["SECRET_KEY"].encode()
    payload = f"{path_with_query}|{exp}".encode()
    good = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, sig)
