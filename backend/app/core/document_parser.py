import re
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile

from app.schemas import UploadedDocument


class DocumentParser:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
    SECTION_HEADING_PATTERN = re.compile(
        r"^\s*(?:[#>*-]+|\d+[.)、-]?|[一二三四五六七八九十]+[.)、-]?)?\s*"
        r"(?:背景|背景资料|线索|关键线索|证据|结果|答案|分析|分析目标|问题|参考分析|时间线|"
        r"background|clues?|evidence|result|answer|analysis|summary|timeline|goal|target)\s*$",
        re.IGNORECASE,
    )

    @classmethod
    async def parse_upload(cls, upload: UploadFile) -> Tuple[UploadedDocument, str]:
        filename = upload.filename or "untitled.txt"
        suffix = Path(filename).suffix.lower()
        if suffix and suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"暂不支持的文件格式: {suffix}")

        data = await upload.read()
        text, page_count = cls._parse_bytes(data, suffix)
        text = cls.preprocess_text(text)
        document = UploadedDocument(
            source_name=filename,
            source_type=suffix.lstrip(".") or "text",
            character_count=len(text),
            page_count=page_count,
            extracted_preview=text[:600],
        )
        return document, text

    @classmethod
    def parse_text(cls, raw_text: str, source_name: str = "direct-input.txt") -> Tuple[UploadedDocument, str]:
        normalized = cls.preprocess_text(raw_text)
        document = UploadedDocument(
            source_name=source_name,
            source_type="text",
            character_count=len(normalized),
            page_count=None,
            extracted_preview=normalized[:600],
        )
        return document, normalized

    @classmethod
    def _parse_bytes(cls, data: bytes, suffix: str) -> Tuple[str, Optional[int]]:
        if suffix == ".pdf":
            return cls._parse_pdf(data)
        return cls._parse_text_bytes(data), None

    @staticmethod
    def _parse_pdf(data: bytes) -> Tuple[str, int]:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError("需要安装 PyMuPDF 才能解析 PDF。") from exc

        text_parts = []
        with fitz.open(stream=data, filetype="pdf") as document:
            page_count = document.page_count
            for page in document:
                text = page.get_text().strip()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts), page_count

    @staticmethod
    def _parse_text_bytes(data: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    @classmethod
    def preprocess_text(cls, text: str) -> str:
        normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("\u3000", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        lines = [line.strip() for line in normalized.split("\n")]
        merged: List[str] = []
        buffer: List[str] = []

        for line in lines:
            if not line:
                if buffer:
                    merged.append(" ".join(buffer).strip())
                    buffer = []
                continue
            if len(line) <= 2 and not any(char.isdigit() for char in line):
                continue
            if cls.SECTION_HEADING_PATTERN.match(line):
                if buffer:
                    merged.append(" ".join(buffer).strip())
                    buffer = []
                merged.append(line)
                continue
            if re.search(r"[:：]$", line) and len(line) <= 20 and buffer:
                merged.append(" ".join(buffer).strip())
                buffer = [line]
                continue
            if buffer and len(line) < 18 and not re.search(r"[。！？!?;；]$", line):
                buffer.append(line)
                continue
            if buffer:
                merged.append(" ".join(buffer).strip())
            buffer = [line]

        if buffer:
            merged.append(" ".join(buffer).strip())

        return "\n".join(segment for segment in merged if segment).strip()

    @classmethod
    def segment_text(cls, text: str) -> List[str]:
        cleaned = cls.preprocess_text(text)
        if not cleaned:
            return []

        rough_parts = re.split(r"\n+|(?<=[。！？!?；;])", cleaned)
        segments: List[str] = []
        for part in rough_parts:
            part = part.strip(" \t-*•#>")
            if not part:
                continue
            if cls.SECTION_HEADING_PATTERN.match(part):
                segments.append(part)
                continue
            if segments and len(part) < 20 and not re.search(r"[:：]$", segments[-1]):
                segments[-1] = f"{segments[-1]} {part}".strip()
            else:
                segments.append(part)
        return segments
