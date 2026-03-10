from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile

from app.schemas import UploadedDocument


class DocumentParser:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}

    @classmethod
    async def parse_upload(cls, upload: UploadFile) -> Tuple[UploadedDocument, str]:
        filename = upload.filename or "untitled.txt"
        suffix = Path(filename).suffix.lower()
        if suffix and suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"暂不支持的文件格式: {suffix}")

        data = await upload.read()
        text, page_count = cls._parse_bytes(data, suffix)
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
        normalized = raw_text.strip()
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
