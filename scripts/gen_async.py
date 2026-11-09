"""Generate ``_async_resources.py`` from ``_resources.py``.

The sync resources are the source of truth. Run after editing them:

    python scripts/gen_async.py          # rewrite
    python scripts/gen_async.py --check  # exit 1 if out of date (CI)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "src" / "solometrics"
SRC = PKG / "_resources.py"
DST = PKG / "_async_resources.py"

HEADER = '"""Asynchronous API resources. GENERATED from ``_resources.py`` by scripts/gen_async.py — do not edit."""'

# Methods that stay synchronous.
SYNC_METHODS = {"__init__", "_conn"}


def transform(src: str) -> str:
    out = src
    out = re.sub(r'\A""".*?"""', HEADER, out, count=1, flags=re.DOTALL)
    out = out.replace("import time\n", "import asyncio\nimport time\n", 1)
    out = out.replace("Iterator,", "AsyncIterator,").replace("Iterator[", "AsyncIterator[")
    out = out.replace("from ._client import Client", "from ._async_client import AsyncClient")
    out = re.sub(r"(?<![\w.])Client\b", "AsyncClient", out)
    out = re.sub(r"\b(?<!_)([A-Z]\w*Resource)\b", r"Async\1", out)

    def make_async(m: re.Match) -> str:
        indent, name = m.group(1), m.group(2)
        if name in SYNC_METHODS:
            return m.group(0)
        return f"{indent}async def {name}("

    out = re.sub(r"^(\s+)def (\w+)\(", make_async, out, flags=re.MULTILINE)

    out = out.replace("time.sleep(", "await asyncio.sleep(")
    out = re.sub(r"\breturn self\.(_get|_send|_client\._request|_wait)\(", r"return await self.\1(", out)
    out = re.sub(r"= self\.(search|hot|list)\(", r"= await self.\1(", out)
    out = out.replace("status = fetch()", "status = await fetch()")
    out = out.replace("fetch: Callable[[], Any]", "fetch: Callable[[], Awaitable[Any]]")
    out = out.replace("from typing import TYPE_CHECKING, Any,", "from typing import TYPE_CHECKING, Any, Awaitable,")
    out = out.replace("Callable[[JobStatus], None]", "Callable[[JobStatus], Any]")
    # on_progress may be sync or async
    out = out.replace(
        "                on_progress(status)\n",
        "                result = on_progress(status)\n"
        "                if asyncio.iscoroutine(result):\n"
        "                    await result\n",
    )
    return out


def ruff(code: str) -> str:
    """Sort imports and format like the rest of the package."""
    for args in (["check", "--select", "I", "--fix", "--quiet"], ["format", "--quiet"]):
        code = subprocess.run(
            [sys.executable, "-m", "ruff", *args, "--stdin-filename", str(DST), "-"],
            input=code,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    return code


def main() -> int:
    generated = ruff(transform(SRC.read_text()))
    if "--check" in sys.argv:
        if not DST.exists() or DST.read_text() != generated:
            print(f"{DST.name} is out of date; run python scripts/gen_async.py")
            return 1
        return 0
    DST.write_text(generated)
    print(f"wrote {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
