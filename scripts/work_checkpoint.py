#!/usr/bin/env python3
"""
Work Progress Checkpoint
Lightweight progress tracking without LLM calls.

Usage:
    python3 work_checkpoint.py --project "OCM Sup" --status "P4 Phase 2 done" --next "waiting for review"
    python3 work_checkpoint.py --done "Completed P4 Integration"
    python3 work_checkpoint.py --show
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Paths
WORKSPACE = Path("/home/jacky/.openclaw/workspace")
CHECKPOINT_FILE = WORKSPACE / "memory" / "work-in-progress.md"
CHECKPOINT_JSON = WORKSPACE / "memory" / "work-in-progress.json"

# Ensure memory directory exists
CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_checkpoint() -> dict:
    """Load existing checkpoint data."""
    if CHECKPOINT_JSON.exists():
        try:
            with open(CHECKPOINT_JSON) as f:
                return json.load(f)
        except:
            pass
    return {
        "project": "Unknown",
        "current_status": "No active work",
        "next_action": "Unknown",
        "last_updated": None,
        "progress_log": []
    }


def save_checkpoint(data: dict):
    """Save checkpoint to both JSON and Markdown."""
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Save JSON (for machine reading)
    with open(CHECKPOINT_JSON, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Save Markdown (for human reading)
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(f"# Work in Progress\n\n")
        f.write(f"**Last Updated:** {data['last_updated']} (UTC)\n\n")
        f.write(f"## Current Project\n**{data['project']}**\n\n")
        f.write(f"**Status:** {data['current_status']}\n\n")
        f.write(f"**Next Action:** {data['next_action']}\n\n")
        
        if data.get("progress_log"):
            f.write(f"## Progress Log\n\n")
            f.write(f"| Time | Action | Status |\n")
            f.write(f"|------|--------|--------|\n")
            for entry in data["progress_log"][-10:]:  # Last 10 entries
                f.write(f"| {entry.get('time', '-')} | {entry.get('action', '-')} | {entry.get('status', '-')} |\n")
            f.write(f"\n")


def update_checkpoint(project: str = None, status: str = None, next_action: str = None, action: str = None, status_flag: str = None):
    """Update checkpoint with new information."""
    data = load_checkpoint()
    
    if project:
        data["project"] = project
    if status:
        data["current_status"] = status
    if next_action:
        data["next_action"] = next_action
    
    # Add progress log entry if action provided
    if action:
        time_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
        log_entry = {
            "time": time_str,
            "action": action,
            "status": status_flag or "done",
            "project": data["project"],
            "status_snapshot": data["current_status"]
        }
        data["progress_log"].append(log_entry)
    
    save_checkpoint(data)
    return data


def show_checkpoint():
    """Display current checkpoint."""
    data = load_checkpoint()
    
    print("=== Work in Progress ===\n")
    print(f"Project: {data['project']}")
    print(f"Status: {data['current_status']}")
    print(f"Next Action: {data['next_action']}")
    print(f"Last Updated: {data['last_updated']}")
    
    if data.get("progress_log"):
        print(f"\nRecent Progress ({len(data['progress_log'])} entries):")
        for entry in data["progress_log"][-5:]:  # Last 5
            print(f"  [{entry.get('time', '-')}] {entry.get('action', '-')} - {entry.get('status', '-')}")
    
    return data


def main():
    parser = argparse.ArgumentParser(description="Work Progress Checkpoint")
    parser.add_argument("--project", "-p", help="Project name")
    parser.add_argument("--status", "-s", help="Current status")
    parser.add_argument("--next", "-n", help="Next action")
    parser.add_argument("--done", "-d", help="Mark as done with description")
    parser.add_argument("--show", action="store_true", help="Show current checkpoint")
    
    args = parser.parse_args()
    
    if args.show or not any([args.project, args.status, args.next, args.done]):
        show_checkpoint()
        return
    
    # Determine status flag based on input
    status_flag = "✅"
    if args.done:
        status_flag = "✅"
        action = args.done
    elif args.status:
        status_flag = "🔄"
        action = args.status
    else:
        action = "checkpoint"
    
    data = update_checkpoint(
        project=args.project,
        status=args.status,
        next_action=args.next,
        action=action,
        status_flag=status_flag
    )
    
    print(f"✅ Checkpoint saved!")
    print(f"   Project: {data['project']}")
    print(f"   Status: {data['current_status']}")
    print(f"   Next: {data['next_action']}")


if __name__ == "__main__":
    main()
