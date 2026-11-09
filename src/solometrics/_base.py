"""Transport-independent pieces shared by the sync and async clients."""

from __future__ import annotations

import csv
import io
import os
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import (
    IO,
    Any,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import httpx

from ._exceptions import _parse_retry_after
from ._version import __version__

DEFAULT_BASE_URL = "https://api.sneakers.itbanque.com"
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
DEFAULT_MAX_RETRIES = 2
API_KEY_ENV = "SOLOMETRICS_API_KEY"
BASE_URL_ENV = "SOLOMETRICS_BASE_URL"

# Background-job statuses after which polling stops.
TERMINAL_JOB_STATUSES = frozenset({"SUCCESS", "FAILURE", "CANCELLED"})

# Methods the API treats as safe to repeat. POST is excluded: retrying a
# create-listing call after a 502/504 could list the same pair twice.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "PATCH", "DELETE"})

_MAX_BACKOFF = 8.0
_MAX_RETRY_AFTER = 60.0


class _Omit:
    """Sentinel for "parameter not given" (distinct from an explicit ``None``)."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "OMIT"


OMIT: Any = _Omit()

Amount = Union[int, float, str, Decimal]
DateLike = Union[str, date, datetime]
FileInput = Union[str, "os.PathLike[str]", bytes, IO[bytes], IO[str]]
Rows = Iterable[Mapping[str, Any]]


@dataclass
class FinalRequestOptions:
    method: str
    path: str
    params: Dict[str, Any] = field(default_factory=dict)
    json: Any = None
    files: Optional[Dict[str, Tuple[str, bytes, str]]] = None
    timeout: Any = None  # None → client default
    max_retries: Optional[int] = None


def resolve_api_key(api_key: Optional[str]) -> str:
    key = api_key or os.environ.get(API_KEY_ENV)
    if not key:
        raise ValueError(f"No API key provided. Pass api_key=... or set the {API_KEY_ENV} environment variable.")
    return key


def resolve_base_url(base_url: Optional[str]) -> str:
    return (base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")


def default_headers(api_key: str) -> Dict[str, str]:
    return {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": f"solometrics-python/{__version__}",
    }


def clean_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop omitted/``None`` values and stringify the rest for the query string."""
    out: Dict[str, Any] = {}
    for key, value in params.items():
        if value is OMIT or value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (date, datetime)):
            out[key] = format_date(value)
        else:
            out[key] = value
    return out


def clean_body(body: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop omitted values from a JSON body. Explicit ``None`` is also dropped:
    no documented body field accepts ``null``."""
    return {k: v for k, v in body.items() if v is not OMIT and v is not None}


def format_amount(amount: Amount) -> str:
    """Prices are sent as strings. ``250``, ``250.0`` and ``"250"`` all become ``"250"``."""
    if isinstance(amount, bool):
        raise TypeError("amount must be a number or string, not bool")
    if isinstance(amount, float) and amount.is_integer():
        return str(int(amount))
    if isinstance(amount, Decimal):
        return format(amount.normalize(), "f") if amount == amount.to_integral() else str(amount)
    return str(amount)


def format_size(size: Union[str, float, Decimal]) -> str:
    if isinstance(size, float) and size.is_integer():
        return str(int(size))
    return str(size)


def format_date(value: DateLike) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def format_datetime(value: Union[str, datetime]) -> str:
    return value.isoformat() if isinstance(value, datetime) else value


def path_segment(value: Any) -> str:
    """Percent-encode a value for use as a single path segment."""
    from urllib.parse import quote

    return quote(str(value), safe="")


def prepare_csv_upload(
    file: Optional[FileInput],
    rows: Optional[Rows],
    *,
    default_name: str,
) -> Dict[str, Tuple[str, bytes, str]]:
    """Turn ``file`` (path, bytes or file object) or ``rows`` (dicts) into a
    multipart ``file`` field. The content is read into memory so the request
    can be retried."""
    if (file is None) == (rows is None):
        raise TypeError("Pass exactly one of `file` or `rows`.")

    if rows is not None:
        content, name = rows_to_csv(rows), default_name
    elif isinstance(file, (bytes, bytearray)):
        content, name = bytes(file), default_name
    elif isinstance(file, (str, os.PathLike)):
        path = os.fspath(file)
        with open(path, "rb") as fh:
            content = fh.read()
        name = os.path.basename(path)
    elif hasattr(file, "read"):
        data = file.read()  # type: ignore[union-attr]
        content = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        raw_name = getattr(file, "name", None)
        name = os.path.basename(raw_name) if isinstance(raw_name, str) else default_name
    else:
        raise TypeError(f"Unsupported file input: {type(file).__name__}")

    # The API only accepts files whose name ends in .csv.
    if not name.lower().endswith(".csv"):
        name = f"{name}.csv"
    return {"file": (name, content, "text/csv")}


def rows_to_csv(rows: Rows) -> bytes:
    rows = list(rows)
    if not rows:
        raise ValueError("`rows` is empty.")
    header: list = []
    for row in rows:
        for key in row:
            if key not in header:
                header.append(key)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return buf.getvalue().encode("utf-8")


def normalize_batch_delete_items(items: Iterable[Any]) -> list:
    """Accept ``{"listingId", "variantId"}`` dicts, snake_case dicts, bare
    listing ID strings or ``(listing_id, variant_id)`` tuples."""
    out = []
    for item in items:
        if isinstance(item, str):
            out.append({"listingId": item})
            continue
        if isinstance(item, (tuple, list)):
            listing_id, variant_id = (list(item) + [None])[:2]
        elif isinstance(item, Mapping):
            listing_id = item.get("listingId", item.get("listing_id"))
            variant_id = item.get("variantId", item.get("variant_id"))
        else:
            raise TypeError(f"Unsupported batch-delete item: {item!r}")
        if not listing_id:
            raise ValueError(f"Batch-delete item is missing a listing ID: {item!r}")
        entry: Dict[str, Any] = {"listingId": listing_id}
        if variant_id:
            entry["variantId"] = variant_id
        out.append(entry)
    if not out:
        raise ValueError("`items` is empty.")
    return out


def join_statuses(statuses: Union[str, Sequence[str], None]) -> Optional[str]:
    if statuses is None or statuses is OMIT:
        return None
    if isinstance(statuses, str):
        return statuses
    return ",".join(statuses)


# --------------------------------------------------------------------------- retries


def should_retry_response(method: str, response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code in (502, 503, 504):
        return method.upper() in _IDEMPOTENT_METHODS
    return False


def should_retry_exception(method: str, exc: Exception) -> bool:
    # A connect failure means the request never reached the server, so it is
    # always safe to repeat. A read timeout may have been processed already.
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)):
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return method.upper() in _IDEMPOTENT_METHODS
    return False


def retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
    """Seconds to wait before retry number ``attempt`` (0-based)."""
    if response is not None:
        retry_after = _parse_retry_after(response)
        if retry_after is not None:
            return min(retry_after, _MAX_RETRY_AFTER)
    base = min(0.5 * (2**attempt), _MAX_BACKOFF)
    return base * (0.75 + random.random() * 0.5)


def job_finished(payload: Any) -> bool:
    status = payload.get("status") if isinstance(payload, dict) else None
    return isinstance(status, str) and status.upper() in TERMINAL_JOB_STATUSES
