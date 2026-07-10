"""Shared crawler utilities."""

from __future__ import annotations


def table_to_prose(table_tag) -> str:
    """Convert an HTML <table> to labelled prose sentences for better embedding.

    Pipe-table cells like '| 32 GB |' carry no semantic meaning without their
    header. Converting each row to 'vCPU: 12, RAM: 32 GB, Disk: 128 GB.' lets
    the embedding model match hardware/config queries correctly.

    Handles:
    - Standard <th> header + <td> data rows
    - All-<td> tables (no explicit header)
    - colspan/rowspan: cells are flattened via get_text — no special handling
    - Nested tables: get_text() recurses into them automatically
    - Empty rows: skipped
    """
    rows = table_tag.find_all("tr")
    if not rows:
        return ""

    has_th = bool(rows[0].find_all("th"))
    header_cells = rows[0].find_all("th") if has_th else rows[0].find_all("td")
    headers = [c.get_text(" ", strip=True) for c in header_cells]
    data_rows = rows[1:] if has_th else rows

    sentences: list[str] = []
    for row in data_rows:
        cells = [td.get_text(" ", strip=True) for td in row.find_all(["th", "td"])]
        if not any(cells):
            continue
        if headers and len(headers) == len(cells):
            parts = [f"{h}: {c}" for h, c in zip(headers, cells) if h and c]
        else:
            parts = [c for c in cells if c]
        if parts:
            sentences.append(", ".join(parts) + ".")
    return "\n".join(sentences)
