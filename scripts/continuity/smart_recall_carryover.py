"""
Smart Recall Carryover Hook
===========================

Connects the continuity layer to OCM Sup's Smart Recall cron job.

This module:
1. Checks for due hooks when the cron job runs
2. Applies sleep/rest suppress
3. Renders follow-up messages
4. Writes to daily memory traces
5. Updates entity status in the wiki

Usage:
    python3 smart_recall_carryover.py --check-due
    python3 smart_recall_carryover.py --check-sleep
    python3 smart_recall_carryover.py --status
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add OCM Sup to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from continuity.hook_lifecycle import HookLifecycle
from continuity.frontstage_guard import FrontstageGuard
from continuity.daily_memory_trace import DailyMemoryTrace
from continuity.state_router import StateRouter
from continuity.carryover import CarryoverManager
from continuity.continuity_state import ContinuityState


def status():
    """Show current status of continuity layer"""
    state = ContinuityState()
    status_data = state.get_status()
    
    print("=" * 60)
    print("CONTINUITY LAYER STATUS")
    print("=" * 60)
    print(f"Version: {status_data['continuity_layer']['version']}")
    print(f"Phase: {status_data['continuity_layer']['phase']}")
    print(f"Enabled: {status_data['continuity_layer']['enabled']}")
    print()
    
    print(f"Current Session:")
    print(f"  Is /new: {status_data['current_session']['is_new_session']}")
    print(f"  Turn count: {status_data['current_session']['turn_count']}")
    print()
    
    print(f"Carryover:")
    print(f"  Has pending: {status_data['carryover']['has_pending_topic']}")
    if status_data['carryover']['pending_topic']:
        pt = status_data['carryover']['pending_topic']
        print(f"  Topic: {pt.get('entity_name', 'N/A')}")
        print(f"  Type: {pt.get('event_type', 'N/A')}")
        print(f"  Created: {pt.get('created', 'N/A')}")
    print()
    
    print(f"Pending Topics: {status_data['pending_topics']['count']}")
    for pt in status_data['pending_topics']['items'][:3]:
        print(f"  - {pt.get('entity_name', 'N/A')} ({pt.get('event_type', 'N/A')})")
    print()
    
    print(f"Time State:")
    print(f"  Phase: {status_data['time_state']['phase']}")
    print(f"  Current time: {status_data['time_state']['current_time']}")
    print(f"  Sleep: {status_data['time_state']['sleep_time']} - {status_data['time_state']['wake_time']}")
    print(f"  Proactive allowed: {status_data['time_state']['is_proactive_allowed']}")
    
    print()
    return status_data


def check_due_hooks():
    """Check for due hooks and render follow-ups"""
    print("=" * 60)
    print("CHECKING DUE HOOKS")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize
    lifecycle = HookLifecycle()
    guard = FrontstageGuard()
    trace = DailyMemoryTrace()
    
    # Check sleep suppress first
    print("Applying sleep suppress...")
    lifecycle.check_and_apply_sleep_suppress()
    
    # Get time state
    time_state = lifecycle.carryover._evaluate_time_state()
    print(f"Current phase: {time_state['phase']}")
    print()
    
    # Check dispatch cap
    stats = lifecycle.get_dispatch_stats()
    print(f"Dispatch stats: {stats['dispatches_today']} / {stats['cap']} today")
    
    if stats['dispatches_today'] >= stats['cap']:
        print("⚠️ Dispatch cap reached for today. Skipping.")
        return []
    
    if not time_state['is_proactive_allowed']:
        print("⚠️ Not in proactive hours (sleep/rest suppress active). Skipping.")
        return []
    
    print()
    
    # Check due hooks
    print("Checking due hooks...")
    due_hooks = lifecycle.check_due_hooks()
    print(f"Found {len(due_hooks)} due hooks")
    
    if not due_hooks:
        print("No hooks due. Done.")
        return []
    
    print()
    
    # Render and display follow-ups
    followups = []
    for hook in due_hooks:
        print(f"- Hook: {hook['id']}")
        print(f"  Entity: {hook['entity_name']}")
        print(f"  Type: {hook['event_type']}")
        print(f"  Followup focus: {hook['followup_focus']}")
        
        # Render message
        message = lifecycle.render_followup(hook['id'])
        print(f"  Raw message: {message[:100]}..." if message and len(message) > 100 else f"  Raw message: {message}")
        
        # Sanitize
        safe_message = guard.sanitize(message) if message else None
        print(f"  Safe message: {safe_message[:100]}..." if safe_message and len(safe_message) > 100 else f"  Safe message: {safe_message}")
        
        if safe_message:
            followups.append({
                'hook_id': hook['id'],
                'message': safe_message,
            })
        
        print()
    
    # Summary
    print(f"Ready to dispatch: {len(followups)} follow-ups")
    
    return followups


def dispatch_followup(hook_id: str, message: str):
    """Dispatch a follow-up message"""
    print("=" * 60)
    print(f"DISPATCHING FOLLOW-UP")
    print("=" * 60)
    
    lifecycle = HookLifecycle()
    guard = FrontstageGuard()
    trace = DailyMemoryTrace()
    
    # Sanitize message
    safe_message = guard.sanitize(message)
    
    if not safe_message:
        print("❌ Message sanitized to empty. Cannot dispatch.")
        return False
    
    # Get hook info before dispatching
    hook = lifecycle.get_hook(hook_id)
    if not hook:
        print(f"❌ Hook {hook_id} not found")
        return False
    
    # Mark as dispatched
    lifecycle.mark_dispatched(hook_id)
    print(f"✅ Marked hook {hook_id} as dispatched")
    
    # Write trace
    trace.write(
        event_type=hook.get('event_type', 'unknown'),
        action='dispatched',
        entity_name=hook.get('entity_name', 'Unknown'),
        topic_id=hook_id,
        causal_memory=hook.get('causal_memory', {}),
        details={
            'message_preview': safe_message[:100],
        },
        severity='info'
    )
    print(f"✅ Wrote dispatch trace to daily memory")
    
    print()
    print(f"Follow-up message to send:")
    print(f"  {safe_message}")
    
    return True


def close_all_pending():
    """Close all pending hooks (for testing)"""
    print("=" * 60)
    print("CLOSING ALL PENDING HOOKS")
    print("=" * 60)
    
    lifecycle = HookLifecycle()
    hooks_path = lifecycle.state_dir / "hooks.json"
    
    if not hooks_path.exists():
        print("No hooks file found")
        return 0
    
    hooks_data = json.loads(hooks_path.read_text())
    closed_count = 0
    
    for hook in hooks_data.get("items", []):
        if hook["status"] not in ["closed", "resolved"]:
            lifecycle.close_hook(hook["id"], "explicit_close")
            closed_count += 1
            print(f"Closed: {hook['id']} ({hook['entity_name']})")
    
    print()
    print(f"Closed {closed_count} hooks")
    
    return closed_count


def cleanup_stale(days_threshold: int = 30):
    """Clean up stale continuity entities"""
    print("=" * 60)
    print(f"CLEANING UP STALE ENTITIES")
    print("=" * 60)
    print(f"Threshold: {days_threshold} days")
    
    # Clean up daily memory traces
    trace = DailyMemoryTrace()
    removed_traces = trace.cleanup_old_traces(days_threshold)
    print(f"Cleaned {removed_traces} old traces")
    
    print()
    print("✅ Cleanup complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Smart Recall Carryover Hook")
    parser.add_argument("--status", action="store_true", help="Show continuity layer status")
    parser.add_argument("--check-due", action="store_true", help="Check for due hooks")
    parser.add_argument("--dispatch", type=str, metavar="HOOK_ID", help="Dispatch a specific hook")
    parser.add_argument("--close-all", action="store_true", help="Close all pending hooks")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up entities older than N days")
    
    args = parser.parse_args()
    
    if args.status:
        status()
    elif args.check_due:
        followups = check_due_hooks()
        if followups:
            print()
            print("Use --dispatch HOOK_ID to dispatch a follow-up")
    elif args.dispatch:
        # Dispatch a hook - need to provide message
        # For now, just mark as dispatched
        lifecycle = HookLifecycle()
        hook = lifecycle.get_hook(args.dispatch)
        if hook:
            lifecycle.mark_dispatched(args.dispatch)
            print(f"Dispatched hook: {args.dispatch}")
        else:
            print(f"Hook not found: {args.dispatch}")
    elif args.close_all:
        close_all_pending()
    elif args.cleanup:
        cleanup_stale(args.cleanup)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
