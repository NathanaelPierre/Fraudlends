"""
Symmetric encryption for storing user-supplied API keys at rest, using
Fernet (AES-128-CBC + HMAC). Protects against a leaked database dump —
not against someone with full server access, which isn't achievable
for a server that needs to use the key live.
"""
import os
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_key = os.getenv("ENCRYPTION_KEY")
if not _key:
    raise RuntimeError(
        "ENCRYPTION_KEY is not set. Generate one with:\n"
        "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        "and add it to .env as ENCRYPTION_KEY=<value>"
    )

_fernet = Fernet(_key.encode())


def encrypt_value(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Could not decrypt value — wrong key or corrupted data")


def mask_key(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "•" * len(plaintext)
    return f"{plaintext[:4]}{'•' * 8}{plaintext[-4:]}"
