import json
from pathlib import Path

from packages.marketplace.signing import generate_keypair, sign_manifest, verify_manifest


def test_manifest_signature_round_trip(tmp_path: Path) -> None:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    generate_keypair(private, public)
    manifest = {"name": "demo", "version": "1.0.0", "package_type": "connector"}
    signature = sign_manifest(manifest, private)
    assert verify_manifest(manifest, signature, public)
    tampered = {**manifest, "version": "1.0.1"}
    assert not verify_manifest(tampered, signature, public)


def test_demo_manifest_is_signed_json() -> None:
    path = Path("examples/marketplace/nexus-demo-connector.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["package_type"] == "connector"
    assert payload["signature"]
