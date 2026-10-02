import argparse
import json
from pathlib import Path

from packages.marketplace.signing import generate_keypair, sign_manifest, verify_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign or verify a NEXUS marketplace manifest")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--private-key", type=Path, default=Path("marketplace-private.pem"))
    parser.add_argument("--public-key", type=Path, default=Path("marketplace-public.pem"))
    parser.add_argument("--generate-keys", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.generate_keys:
        generate_keypair(args.private_key, args.public_key)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.verify:
        signature = manifest.get("signature", "")
        if not signature or not verify_manifest(manifest, signature, args.public_key):
            raise SystemExit("manifest signature verification failed")
        print("signature: valid")
        return
    manifest["signature"] = sign_manifest(manifest, args.private_key)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("signature: written")


if __name__ == "__main__":
    main()
