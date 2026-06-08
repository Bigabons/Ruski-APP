"""
Enrich seed/words.json using Yandex Dictionary API.
- Adds IPA transcription field to each word entry
- Reports translation differences vs Yandex for manual review
- Updates words.json in place

Usage: python enrich_words.py
"""
import json
import os
import time
import warnings
from pathlib import Path

import requests
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

API_KEY = os.getenv("YANDEX_DICT_KEY", "")
if not API_KEY:
    raise SystemExit("Set YANDEX_DICT_KEY env variable before running this script.")
BASE = "https://dictionary.yandex.net/api/v1/dicservice.json"
SEED = Path(__file__).parent / "seed" / "words.json"


def get_langs() -> list:
    r = requests.get(f"{BASE}/getLangs", params={"key": API_KEY}, verify=False, timeout=8)
    r.raise_for_status()
    return r.json()


def lookup(text: str, lang: str) -> dict:
    r = requests.get(
        f"{BASE}/lookup",
        params={"key": API_KEY, "lang": lang, "text": text},
        verify=False, timeout=8,
    )
    r.raise_for_status()
    return r.json()


def best(result: dict) -> tuple:
    """Returns (pl_translation | None, ipa | None)"""
    defs = result.get("def", [])
    if not defs:
        return None, None
    d = defs[0]
    ipa = d.get("ts")
    trs = d.get("tr", [])
    pl = trs[0]["text"] if trs else None
    return pl, ipa


def main():
    langs = get_langs()
    lang = "ru-pl" if "ru-pl" in langs else "ru-en"
    print(f"Using lang pair: {lang}")
    if lang == "ru-en":
        print("  (ru-pl not in Yandex Dict — using ru-en for IPA only, skipping PL comparison)")

    words = json.loads(SEED.read_text("utf-8"))
    diffs = []
    no_result = []
    ipa_added = 0

    for w in words:
        if w["typ"] != "slowo":
            continue  # Yandex Dict works for single words, not phrases

        try:
            res = lookup(w["ru"], lang)
            pl_yandex, ipa = best(res)

            if ipa and "ipa" not in w:
                w["ipa"] = ipa
                ipa_added += 1

            if pl_yandex is None:
                no_result.append(w["ru"])
                continue

            if lang == "ru-pl":
                our = w["pl"].lower().split(" / ")[0].split(" (")[0].strip()
                theirs = pl_yandex.lower().strip()
                if our != theirs:
                    diffs.append({
                        "ru": w["ru"], "our": w["pl"],
                        "yandex": pl_yandex, "ipa": ipa,
                    })

        except Exception as e:
            print(f"  ERROR [{w['ru']}]: {e}")

        time.sleep(0.06)

    SEED.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nIPA added to {ipa_added} words.")

    if no_result:
        print(f"No result from Yandex ({len(no_result)}): {', '.join(no_result)}")

    if lang == "ru-pl":
        print(f"\nTranslation diffs ({len(diffs)}):")
        if not diffs:
            print("  None — everything matches!")
        for d in diffs:
            print(f"  {d['ru']}")
            print(f"    ours  : {d['our']}")
            print(f"    yandex: {d['yandex']}")
            if d["ipa"]:
                print(f"    ipa   : [{d['ipa']}]")


if __name__ == "__main__":
    main()
