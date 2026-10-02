import base64
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_bytes(manifest: dict[str, Any]) -> bytes:
    clean = dict(manifest)
    clean.pop("signature", None)
    return json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_keypair(private_path: Path, public_path: Path) -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def sign_manifest(manifest: dict[str, Any], private_path: Path) -> str:
    private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise TypeError("Signing key must be Ed25519")
    return base64.urlsafe_b64encode(private.sign(canonical_bytes(manifest))).decode("ascii")


def verify_manifest(manifest: dict[str, Any], signature: str, public_path: Path) -> bool:
    public = serialization.load_pem_public_key(public_path.read_bytes())
    if not isinstance(public, Ed25519PublicKey):
        raise TypeError("Verification key must be Ed25519")
    try:
        public.verify(
            base64.urlsafe_b64decode(signature.encode("ascii")), canonical_bytes(manifest)
        )
        return True
    except Exception:
        return False
