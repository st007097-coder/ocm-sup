"""
Fact Archiver - stores pruned facts for recovery within TTL window.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

ARCHIVE_DIR = Path("~/.openclaw/ocm-sup/archive").expanduser()
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


class FactArchiver:
    """
    Archives deleted facts for recovery within TTL window.

    Storage format:
        archive/
            2026-04-28/
                fact_abc123.json
                fact_def456.json
            2026-04-27/
                ...
    """

    def __init__(self, ttl_days: int = 30):
        self.ttl_days = ttl_days

    def archive(self, fact_id: str, fact_text: str, fact_data: dict) -> str:
        """
        Archive a fact before deletion.

        Args:
            fact_id: ID of the fact
            fact_text: Text content of the fact
            fact_data: Full fact data dict

        Returns:
            Path to archived file
        """
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = ARCHIVE_DIR / today
        date_dir.mkdir(parents=True, exist_ok=True)

        archive_file = date_dir / f"{fact_id}.json"

        archive_entry = {
            "fact_id": fact_id,
            "text": fact_text,
            "data": fact_data,
            "archived_at": datetime.now().isoformat(),
            "ttl_expires_at": (
                datetime.now().replace(hour=23, minute=59, second=59) +
                timedelta(days=self.ttl_days)
            ).isoformat()
        }

        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(archive_entry, f, ensure_ascii=False, indent=2)

        return str(archive_file)

    def restore(self, fact_id: str) -> Optional[dict]:
        """
        Restore a recently archived fact.

        Args:
            fact_id: ID of the fact to restore

        Returns:
            Fact data dict if found, None if not found or expired
        """
        # Search all archive directories
        if not ARCHIVE_DIR.exists():
            return None

        for date_dir in ARCHIVE_DIR.iterdir():
            if not date_dir.is_dir():
                continue

            archive_file = date_dir / f"{fact_id}.json"
            if not archive_file.exists():
                continue

            with open(archive_file, "r", encoding="utf-8") as f:
                entry = json.load(f)

            # Check TTL
            expires_at = datetime.fromisoformat(entry["ttl_expires_at"])
            if datetime.now() > expires_at:
                # Expired - delete and return None
                archive_file.unlink()
                return None

            return entry["data"]

        return None

    def cleanup_expired(self) -> int:
        """
        Remove expired archives.

        Returns:
            Number of archives removed
        """
        if not ARCHIVE_DIR.exists():
            return 0

        removed = 0
        now = datetime.now()

        for date_dir in ARCHIVE_DIR.iterdir():
            if not date_dir.is_dir():
                continue

            for archive_file in date_dir.iterdir():
                if not archive_file.name.endswith(".json"):
                    continue

                try:
                    with open(archive_file, "r", encoding="utf-8") as f:
                        entry = json.load(f)

                    expires_at = datetime.fromisoformat(entry["ttl_expires_at"])
                    if now > expires_at:
                        archive_file.unlink()
                        removed += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Corrupted file - remove
                    archive_file.unlink()
                    removed += 1

        return removed

    def list_archived(self, date: str = None) -> list[dict]:
        """
        List archived facts.

        Args:
            date: Optional date string (YYYY-MM-DD) to filter

        Returns:
            list of archive entry dicts
        """
        if not ARCHIVE_DIR.exists():
            return []

        results = []

        for date_dir in ARCHIVE_DIR.iterdir():
            if not date_dir.is_dir():
                continue

            if date and date_dir.name != date:
                continue

            for archive_file in date_dir.iterdir():
                if not archive_file.name.endswith(".json"):
                    continue

                try:
                    with open(archive_file, "r", encoding="utf-8") as f:
                        entry = json.load(f)
                    results.append(entry)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return results

    def count(self) -> dict:
        """Get archive statistics."""
        if not ARCHIVE_DIR.exists():
            return {"dates": 0, "total_facts": 0}

        dates = list(d for d in ARCHIVE_DIR.iterdir() if d.is_dir())
        total = sum(1 for d in dates for f in d.iterdir() if f.name.endswith(".json"))

        return {
            "dates": len(dates),
            "total_facts": total,
            "ttl_days": self.ttl_days
        }


# Import timedelta for archive TTL calculation
from datetime import timedelta