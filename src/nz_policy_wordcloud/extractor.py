"""HTML text extraction, fallback processing, and inspectable source records."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import trafilatura

# Minimum text characters to qualify as a valid substantive policy extraction
DEFAULT_MIN_CHARACTERS: int = 50


class ExtractionStatus(str, Enum):
    """Categorized status of the text extraction outcome."""

    SUCCESS_PRIMARY = "success_primary"
    SUCCESS_FALLBACK = "success_fallback"
    EMPTY_CONTENT = "empty_content"
    TOO_SHORT = "too_short"
    EXTRACTION_FAILED = "extraction_failed"


@dataclass
class ExtractedDocument:
    """Substantive text extracted from an HTML page with source traceability."""

    party_id: str
    source_url: str
    final_url: str
    status: ExtractionStatus
    extraction_method: str
    title: str | None = None
    text: str = ""
    character_count: int = 0
    word_count: int = 0
    timestamp_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_usable(self) -> bool:
        """Check if extraction yielded substantive text for analysis."""
        return self.status in {
            ExtractionStatus.SUCCESS_PRIMARY,
            ExtractionStatus.SUCCESS_FALLBACK,
        } and self.word_count > 0

    def format_for_storage(self) -> str:
        """Format document text with YAML metadata header for file storage."""
        lines = [
            "---",
            f"party_id: {self.party_id}",
            f"source_url: {self.source_url}",
            f"final_url: {self.final_url}",
            f"status: {self.status.value}",
            f"extraction_method: {self.extraction_method}",
            f"character_count: {self.character_count}",
            f"word_count: {self.word_count}",
            f"timestamp_iso: {self.timestamp_iso}",
        ]
        if self.title:
            escaped_title = self.title.replace('"', '\\"')
            lines.append(f'title: "{escaped_title}"')
        lines.append("---")
        lines.append("")
        lines.append(self.text.strip())
        lines.append("")
        return "\n".join(lines)

    def get_safe_filename(self) -> str:
        """Generate a safe, unique filename derived from source URL and party ID."""
        parsed = urlparse(self.source_url)
        path_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", parsed.path.strip("/")).strip("_")
        if not path_slug:
            path_slug = "index"
        path_slug = path_slug[:40]

        url_hash = hashlib.sha256(self.source_url.encode("utf-8")).hexdigest()[:8]
        return f"{self.party_id}_{path_slug}_{url_hash}.txt"

    def to_dict(self) -> dict[str, Any]:
        """Convert document metadata to dictionary for manifests and reporting."""
        return {
            "party_id": self.party_id,
            "source_url": self.source_url,
            "final_url": self.final_url,
            "status": self.status.value,
            "extraction_method": self.extraction_method,
            "title": self.title or "",
            "character_count": self.character_count,
            "word_count": self.word_count,
            "timestamp_iso": self.timestamp_iso,
        }


class HtmlExtractor:
    """Extracts readable content from HTML pages using trafilatura with BeautifulSoup fallback."""

    def __init__(self, min_characters: int = DEFAULT_MIN_CHARACTERS) -> None:
        self.min_characters = min_characters

    def _extract_title(self, html: str) -> str | None:
        """Extract page title from HTML title tag."""
        try:
            soup = BeautifulSoup(html[:10000], "html.parser")
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                return title_tag.string.strip()
        except Exception:
            pass
        return None

    def _fallback_extract(self, html: str) -> str:
        """Fallback extraction using BeautifulSoup when primary extraction fails."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Strip noise elements
            for tag in soup.find_all(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "noscript",
                    "aside",
                    "form",
                    "svg",
                ]
            ):
                tag.decompose()

            # Target substantive container if available
            container = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=re.compile(r"(content|policy|article|main)", re.I))
                or soup.body
                or soup
            )

            # Get text preserving paragraph separation
            lines = [
                line.strip()
                for line in container.get_text(separator="\n").splitlines()
            ]
            return "\n".join(line for line in lines if line)
        except Exception:
            return ""

    def extract_document(
        self,
        party_id: str,
        source_url: str,
        final_url: str,
        html: str | None,
    ) -> ExtractedDocument:
        """Extract readable text from HTML, preserving origin traceability and reporting quality."""
        if not html or not html.strip():
            return ExtractedDocument(
                party_id=party_id,
                source_url=source_url,
                final_url=final_url,
                status=ExtractionStatus.EMPTY_CONTENT,
                extraction_method="none",
                text="",
            )

        title = self._extract_title(html)

        # 1. Primary extraction with trafilatura
        primary_text: str | None = None
        try:
            primary_text = trafilatura.extract(
                html,
                url=final_url,
                include_links=False,
                include_images=False,
                output_format="txt",
                favor_precision=True,
            )
        except Exception:
            primary_text = None

        if primary_text and len(primary_text.strip()) >= self.min_characters:
            clean_text = primary_text.strip()
            return ExtractedDocument(
                party_id=party_id,
                source_url=source_url,
                final_url=final_url,
                status=ExtractionStatus.SUCCESS_PRIMARY,
                extraction_method="trafilatura",
                title=title,
                text=clean_text,
                character_count=len(clean_text),
                word_count=len(clean_text.split()),
            )

        # 2. Fallback extraction with BeautifulSoup
        fallback_text = self._fallback_extract(html).strip()
        if fallback_text and len(fallback_text) >= self.min_characters:
            return ExtractedDocument(
                party_id=party_id,
                source_url=source_url,
                final_url=final_url,
                status=ExtractionStatus.SUCCESS_FALLBACK,
                extraction_method="beautifulsoup_fallback",
                title=title,
                text=fallback_text,
                character_count=len(fallback_text),
                word_count=len(fallback_text.split()),
            )

        if fallback_text:
            return ExtractedDocument(
                party_id=party_id,
                source_url=source_url,
                final_url=final_url,
                status=ExtractionStatus.TOO_SHORT,
                extraction_method="beautifulsoup_fallback",
                title=title,
                text=fallback_text,
                character_count=len(fallback_text),
                word_count=len(fallback_text.split()),
            )

        return ExtractedDocument(
            party_id=party_id,
            source_url=source_url,
            final_url=final_url,
            status=ExtractionStatus.EMPTY_CONTENT,
            extraction_method="none",
            title=title,
            text="",
        )

    def save_document(self, doc: ExtractedDocument, output_dir: Path) -> Path:
        """Save extracted document with its metadata header to disk."""
        party_dir = output_dir / "raw_text" / doc.party_id
        party_dir.mkdir(parents=True, exist_ok=True)

        target_file = party_dir / doc.get_safe_filename()
        target_file.write_text(doc.format_for_storage(), encoding="utf-8")
        return target_file

    def extract_from_manifest(
        self,
        manifest: Any,
    ) -> list[ExtractedDocument]:
        """Extract documents from all successful records in a CrawlManifest."""
        documents: list[ExtractedDocument] = []
        for record in manifest.records:
            if record.success and record.html:
                doc = self.extract_document(
                    party_id=record.party_id,
                    source_url=record.attempted_url,
                    final_url=record.final_url or record.attempted_url,
                    html=record.html,
                )
                if doc.status in (
                    ExtractionStatus.SUCCESS_PRIMARY,
                    ExtractionStatus.SUCCESS_FALLBACK,
                ):
                    documents.append(doc)
        return documents
