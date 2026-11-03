#!/usr/bin/env python3
"""Introvert Club SUZURI draft creator. Read-only by default; never updates originals."""
import argparse, base64, json, os, pathlib, urllib.request, urllib.error

API = "https://suzuri.jp/api/v1"
SOURCE_PRODUCT_ID = 19942047

def request(path, token, method="GET", payload=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never print token or potentially sensitive response bodies.
        raise RuntimeError(f"SUZURI API returned HTTP {exc.code} for {method} {path}") from None

def data_uri(path):
    p = pathlib.Path(path)
    if not p.is_file() or p.suffix.lower() != ".png":
        raise ValueError(f"PNG file required: {p}")
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")

def main():
    parser = argparse.ArgumentParser(description="Create a private SUZURI T-shirt from two PNG files")
    parser.add_argument("--front", required=True, help="Existing brand logo PNG")
    parser.add_argument("--back", required=True, help="Transparent back-design PNG")
    parser.add_argument("--title", default="友達募集中です | Introvert Club")
    parser.add_argument("--create", action="store_true", help="Actually create a private product")
    args = parser.parse_args()
    token = os.environ.get("SUZURI_API_TOKEN")
    if not token:
        raise SystemExit("Set SUZURI_API_TOKEN in your environment (never commit it).")
    source = request(f"/products/{SOURCE_PRODUCT_ID}", token)
    product = source.get("product", source)
    item = product.get("item", {})
    material = product.get("material", {})
    if item.get("name") != "t-shirt" or not item.get("isMultiPrintable"):
        raise SystemExit("Source is not a supported multi-print T-shirt; stopped.")
    if not {"front", "back"}.issubset(set(item.get("availablePrintPlaces", []))):
        raise SystemExit("Source does not support front and back; stopped.")
    # Item 1 is the standard T-shirt in SUZURI's API documentation.
    item_id = item["id"]
    if item_id != 1:
        raise SystemExit(f"Unexpected item ID {item_id}; stopped for review.")
    payload = {
        "texture": data_uri(args.front),
        "title": args.title,
        "description": "Introvert Club | 言えないことを、背中で言う。",
        "price": int(material.get("price") or 0),
        "products": [{
            "itemId": item_id,
            "published": False,
            "resizeMode": "contain",
            "sub_materials": [{
                "texture": data_uri(args.back),
                "printSide": "back",
                "enabled": True
            }]
        }]
    }
    print(json.dumps({
        "source_product_id": SOURCE_PRODUCT_ID,
        "source_item_id": item_id,
        "title": args.title,
        "price_margin_yen": payload["price"],
        "front_png": args.front,
        "back_png": args.back,
        "published": False,
        "action": "CREATE_PRIVATE" if args.create else "DRY_RUN_NO_CHANGES",
        "warning": "Print size and placement require visual review; logo left-chest placement is not guaranteed."
    }, ensure_ascii=False, indent=2))
    if not args.create:
        print("No product was created. Pass --create only after reviewing the summary.")
        return
    result = request("/materials", token, method="POST", payload=payload)
    new_material = result.get("material", {})
    print("Created private material ID:", new_material.get("id", "check SUZURI dashboard"))
    print("Review front/back placement and publication state in SUZURI before publishing.")

if __name__ == "__main__":
    main()
