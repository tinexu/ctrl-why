import hashlib
import re
from uuid import NAMESPACE_URL, uuid5

from app.domain.indexing import CodeChunk
from app.domain.parsing import SourceFile, SourceSymbol


def _line_windows(start: int, end: int, max_lines: int, overlap: int):
    cursor = start
    while cursor <= end:
        window_end = min(end, cursor + max_lines - 1)
        yield cursor, window_end
        if window_end == end:
            break
        cursor = window_end - overlap + 1


def build_chunks(
    workspace_id: str,
    files: list[SourceFile],
    symbols: list[SourceSymbol],
    sources: dict[str, str],
    max_lines: int = 120,
    overlap: int = 15,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    symbols_by_file: dict[str, list[SourceSymbol]] = {}
    for symbol in symbols:
        symbols_by_file.setdefault(symbol.file_id, []).append(symbol)

    for file in files:
        lines = sources[file.path].splitlines()
        file_symbols = symbols_by_file.get(file.id, [])
        spans = [(symbol.start_line, symbol.end_line, symbol.id) for symbol in file_symbols]
        if lines:
            covered = [False] * len(lines)
            for start, end, _ in spans:
                for line_number in range(max(1, start), min(len(lines), end) + 1):
                    covered[line_number - 1] = True
            gap_start: int | None = None
            for offset, is_covered in enumerate((*covered, True), start=1):
                if not is_covered and gap_start is None:
                    gap_start = offset
                elif is_covered and gap_start is not None:
                    spans.append((gap_start, offset - 1, None))
                    gap_start = None
        spans.sort(key=lambda span: (span[0], span[1], span[2] or ""))
        for start, end, symbol_id in spans:
            for window_start, window_end in _line_windows(start, end, max_lines, overlap):
                content = "\n".join(lines[window_start - 1 : window_end])
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                chunk_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        f"{workspace_id}:{file.path}:{symbol_id}:{window_start}:{window_end}:{content_hash}",
                    )
                )
                chunks.append(
                    CodeChunk(
                        id=chunk_id,
                        file_id=file.id,
                        symbol_id=symbol_id,
                        path=file.path,
                        start_line=window_start,
                        end_line=window_end,
                        content=content,
                        content_hash=content_hash,
                        token_estimate=len(re.findall(r"\S+", content)),
                    )
                )
    return chunks
