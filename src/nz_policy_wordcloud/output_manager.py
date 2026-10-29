"""Run directory management, CSV/text/PNG output organisation, and run metadata."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nz_policy_wordcloud.analysis import TermRank, export_ranks_to_csv
from nz_policy_wordcloud.crawler import CrawlManifest
from nz_policy_wordcloud.extractor import ExtractedDocument, HtmlExtractor
from nz_policy_wordcloud.visualiser import build_wordcloud_filename, generate_wordcloud_png


def make_run_directory(base_dir: str | Path = "outputs") -> Path:
    """Create a timestamped, non-overwriting run directory under base_dir."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(base_dir) / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


class OutputManager:
    """Coordinates all output artefacts for a single analysis run."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir

    # ------------------------------------------------------------------ #
    # Manifest                                                             #
    # ------------------------------------------------------------------ #

    def save_crawl_manifest(self, manifest: CrawlManifest) -> Path:
        """Write crawl manifest CSV with per-page attempt metadata."""
        out = self.run_dir / "manifest.csv"
        rows = manifest.to_dict_list()
        if not rows:
            out.write_text("", encoding="utf-8")
            return out
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return out

    # ------------------------------------------------------------------ #
    # Raw extracted text                                                   #
    # ------------------------------------------------------------------ #

    def save_extracted_documents(
        self,
        documents: list[ExtractedDocument],
        extractor: HtmlExtractor | None = None,
    ) -> list[Path]:
        """Persist each extracted document as a text file with YAML metadata header."""
        _extractor = extractor or HtmlExtractor()
        saved: list[Path] = []
        for doc in documents:
            saved_path = _extractor.save_document(doc, self.run_dir)
            saved.append(saved_path)
        return saved

    # ------------------------------------------------------------------ #
    # Frequency CSVs                                                       #
    # ------------------------------------------------------------------ #

    def save_frequency_csv(
        self,
        all_party_ranks: dict[str, list[TermRank]],
        top_n: int = 20,
    ) -> tuple[Path, Path]:
        """Export frequency top-N and full-term CSVs, returning both paths."""
        csv_dir = self.run_dir / "csv"
        csv_dir.mkdir(exist_ok=True)

        top_path = csv_dir / "frequency_top20.csv"
        all_path = csv_dir / "frequency_all.csv"

        top_ranks: list[TermRank] = []
        all_ranks: list[TermRank] = []
        for party_id, ranks in all_party_ranks.items():
            all_ranks.extend(ranks)
            top_ranks.extend(ranks[:top_n])

        export_ranks_to_csv(top_ranks, top_path)
        export_ranks_to_csv(all_ranks, all_path)
        return top_path, all_path

    # ------------------------------------------------------------------ #
    # TF-IDF CSVs                                                          #
    # ------------------------------------------------------------------ #

    def save_tfidf_csv(
        self,
        all_party_ranks: dict[str, list[TermRank]],
        top_n: int = 20,
    ) -> tuple[Path, Path]:
        """Export TF-IDF top-N and full-term CSVs, returning both paths."""
        csv_dir = self.run_dir / "csv"
        csv_dir.mkdir(exist_ok=True)

        top_path = csv_dir / "tfidf_top20.csv"
        all_path = csv_dir / "tfidf_all.csv"

        top_ranks: list[TermRank] = []
        all_ranks: list[TermRank] = []
        for party_id, ranks in all_party_ranks.items():
            all_ranks.extend(ranks)
            top_ranks.extend(ranks[:top_n])

        export_ranks_to_csv(top_ranks, top_path)
        export_ranks_to_csv(all_ranks, all_path)
        return top_path, all_path

    # ------------------------------------------------------------------ #
    # Word cloud PNGs                                                      #
    # ------------------------------------------------------------------ #

    def save_wordclouds(
        self,
        frequency_ranks: dict[str, list[TermRank]],
        tfidf_ranks: dict[str, list[TermRank]],
    ) -> dict[str, list[Path]]:
        """Generate and save frequency + TF-IDF PNG word clouds per party.

        Returns:
            Mapping of party_id → list of saved PNG paths (may be empty if no data).
        """
        clouds_dir = self.run_dir / "wordclouds"
        clouds_dir.mkdir(exist_ok=True)

        saved: dict[str, list[Path]] = {}

        all_party_ids = set(frequency_ranks) | set(tfidf_ranks)
        for party_id in sorted(all_party_ids):
            party_paths: list[Path] = []

            # Frequency cloud
            freq_ranks = frequency_ranks.get(party_id, [])
            if freq_ranks:
                freq_filename = build_wordcloud_filename(party_id, "frequency")
                freq_path = generate_wordcloud_png(
                    freq_ranks,
                    clouds_dir / freq_filename,
                    title=f"{party_id} — Term Frequency (reflects repetition in collected text, not policy importance)",
                )
                if freq_path:
                    party_paths.append(freq_path)

            # TF-IDF cloud
            tf_ranks = tfidf_ranks.get(party_id, [])
            if tf_ranks:
                tf_filename = build_wordcloud_filename(party_id, "tfidf")
                tf_path = generate_wordcloud_png(
                    tf_ranks,
                    clouds_dir / tf_filename,
                    title=f"{party_id} — TF-IDF (reflects relative distinctiveness within included party set, not policy importance)",
                )
                if tf_path:
                    party_paths.append(tf_path)

            saved[party_id] = party_paths

        return saved

    # ------------------------------------------------------------------ #
    # Run summary metadata                                                 #
    # ------------------------------------------------------------------ #

    def save_run_summary(self, metadata: dict[str, Any]) -> Path:
        """Save a JSON run summary with collection scope, counts, and known limitations."""
        metadata.setdefault("generated_at_utc", datetime.now(timezone.utc).isoformat())
        metadata.setdefault(
            "disclaimer",
            (
                "Word clouds and term rankings describe patterns in the collected text. "
                "They do not establish policy importance, intent, truth, or outcomes. "
                "TF-IDF distinctiveness is relative to the parties included in this run only. "
                "Collection may be incomplete; JavaScript-rendered and PDF content is not collected."
            ),
        )
        summary_path = self.run_dir / "run_summary.json"
        summary_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return summary_path
