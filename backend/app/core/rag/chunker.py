"""文档切分：按段落聚合，控制块大小与重叠。"""
from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 60) -> list[str]:
    """将长文本切分为带重叠的片段。

    优先按段落（双换行）聚合，段落过长时按句子切，最终按字符兜底。
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        if len(buffer) + len(para) + 2 <= chunk_size:
            buffer = f"{buffer}\n\n{para}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            if len(para) > chunk_size:
                # 段落超长：按句子细分
                for piece in _split_long(para, chunk_size, overlap):
                    chunks.append(piece)
                buffer = ""
            else:
                buffer = para

    if buffer:
        chunks.append(buffer)

    # 应用重叠：前一块尾部 overlap 字符作为下一块前缀（已在 _split_long 中处理超长段）
    return [c for c in chunks if c]


def _split_long(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[。！？.!?])", text)
    pieces: list[str] = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) <= chunk_size:
            cur += s
        else:
            if cur:
                pieces.append(cur)
            cur = s[-overlap:] if overlap and len(s) > overlap else s
    if cur:
        pieces.append(cur)
    return pieces
