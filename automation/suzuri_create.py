#!/usr/bin/env python3
"""Prepare/create a private Introvert Club SUZURI T-shirt. Dry-run by default."""
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = "https://suzuri.jp/api/v1"
SOURCE_MATERIAL_ID = 19942047
SHOP_NAME = "introvert-club"
ITEM_ID = 1

def api(path, token, method="GET", payload=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        with urlopen(Request(API + path, headers=headers, data=data, method=method), timeout=40) as r:
            return json.load(r)
    except HTTPError as err:
        raise RuntimeError(f"SUZURI {method} {path.split('?')[0]}: HTTP {err.code}") from None

def png_uri(path):
    p = Path(path)
    if not p.is_file() or p.suffix.lower() != ".png":
        raise ValueError(f"PNG file not found: {p}")
    sig = p.read_bytes()[:8]
    if sig != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG: {p}")
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--front", required=True, help="Brand logo PNG")
    parser.add_argument("--back", required=True, help="Transparent message PNG")
    parser.add_argument("--title", default="友達募集中です | Introvert Club")
    parser.add_argument("--create", action="store_true", help="Create a PRIVATE new product (write operation)")
    args = parser.parse_args()

    token = os.getenv("SUZURI_API_TOKEN")
    if not token:
        raise SystemExit("SUZURI_API_TOKEN is missing. Never paste it into source code.")

    user = api("/user", token).get("user", {})
    if user.get("name") != SHOP_NAME:
        raise SystemExit("The API key is not for introvert-club. Nothing created.")

    products = api(f"/products?materialId={SOURCE_MATERIAL_ID}&itemId={ITEM_ID}&userName={SHOP_NAME}", token).get("products", [])
    matches = [p for p in products if p.get("material", {}).get("id") == SOURCE_MATERIAL_ID and p.get("item", {}).get("id") == ITEM_ID]
    if len(matches) != 1:
        raise SystemExit(f"Expected one matching source product, got {len(matches)}. Nothing created.")
    product = matches[0]
    item = product["item"]
    if not item.get("isMultiPrintable") or not {"front", "back"}.issubset(item.get("availablePrintPlaces", [])):
        raise SystemExit("Source T-shirt does not support front and back printing.")

    margin = product.get("material", {}).get("price")
    if type(margin) is not int or margin < 0:
        raise SystemExit("Cannot verify the existing product's margin. Nothing created.")

    # First texture is the primary material; the sub-material prints on the back.
    payload = {
        "texture": png_uri(args.front),
        "title": args.title,
        "description": "Introvert Club | 言えないことを、背中で言う。",
        "price": margin,
        "products": [{
            "itemId": ITEM_ID,
            "published": False,
            "resizeMode": "contain",
            "sub_materials": [{
                "texture": png_uri(args.back),
                "printSide": "back",
                "enabled": True,
            }],
        }],
    }
    print(json.dumps({
        "action": "CREATE_PRIVATE" if args.create else "DRY_RUN",
        "source_material_id": SOURCE_MATERIAL_ID,
        "source_product_id": product["id"],
        "title": args.title,
        "margin_yen": margin,
        "published": False,
        "front_file": args.front,
        "back_file": args.back,
        "warning": "Left-chest placement and print size are not verified. Inspect SUZURI preview before publishing.",
    }, ensure_ascii=False, indent=2))
    if not args.create:
        print("Dry-run only. No SUZURI changes made.")
        return
    # This is an intentional PRIVATE trial. Existing product is never updated.
    # API does not support copying the original scale/offset at creation.
    existing = api("/materials?limit=50", token).get("materials", [])
    if any(m.get("title") == args.title for m in existing):
        raise SystemExit("Trial title already exists among recent materials. Refusing duplicate creation.")
    result = api("/materials", token, method="POST", payload=payload)
    created = result.get("material", {})
    new_id = created.get("id")
    if not new_id or new_id == SOURCE_MATERIAL_ID:
        raise SystemExit("Unexpected creation response. Inspect SUZURI dashboard; do not retry blindly.")
    print("NEW MATERIAL ID:", new_id)
    print("NEW PRODUCT IDs:", [p.get("id") for p in result.get("products", [])])
    print("Creation response publication flags:", {
        "material": created.get("published"),
        "products": [p.get("published") for p in result.get("products", [])],
    })
    print("Review print placement in SUZURI before publishing.")
    print("Private material created. ID:", result.get("material", {}).get("id", "see SUZURI dashboard"))
    print("Check print position, product price and publication status in SUZURI.")

if __name__ == "__main__":
    main()
