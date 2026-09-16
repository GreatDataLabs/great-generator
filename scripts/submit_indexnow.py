from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence

HOST = "greatdatalabs.github.io"
ENDPOINT = "https://api.indexnow.org/indexnow"


def submit_urls(urls: Sequence[str], key: str) -> dict[str, object]:
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"https://{HOST}/great-generator/{key}.txt",
        "urlList": list(urls),
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return {"status": response.status, "reason": response.reason}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit changed Great Generator URLs to IndexNow.")
    parser.add_argument("urls", nargs="+", help="Fully qualified public URLs to submit.")
    args = parser.parse_args(argv)

    key = os.environ.get("INDEXNOW_KEY")
    if not key:
        print("INDEXNOW_KEY is not set. No URLs were submitted.", file=sys.stderr)
        return 2

    try:
        result = submit_urls(args.urls, key)
    except urllib.error.HTTPError as exc:
        print(f"IndexNow rejected the request: HTTP {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"IndexNow request failed: {exc.reason}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
