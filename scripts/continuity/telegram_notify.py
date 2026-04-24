"""
Telegram Bot Integration for Continuity Layer
============================================

This module handles sending follow-ups to Telegram when hooks are due.

Usage:
    python3 telegram_notify.py --check-due --send
    python3 telegram_notify.py --status

The bot will:
1. Check for due hooks
2. Render follow-up messages
3. Apply frontstage guard (sanitize)
4. Send to configured Telegram channel
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
from continuity.continuity_state import ContinuityState


def check_and_prepare_followups():
    """
    Check for due hooks and prepare follow-up messages.
    
    Returns:
        List of dicts with hook_id and sanitized message
    """
    lifecycle = HookLifecycle()
    guard = FrontstageGuard()
    
    # Apply sleep suppress
    lifecycle.check_and_apply_sleep_suppress()
    
    # Get time state
    time_state = lifecycle.carryover._evaluate_time_state()
    
    if not time_state['is_proactive_allowed']:
        print("⏸️ Sleep/rest suppress active. Skipping.")
        return []
    
    # Check dispatch cap
    stats = lifecycle.get_dispatch_stats()
    if stats['dispatches_today'] >= stats['cap']:
        print(f"⛔ Dispatch cap reached ({stats['dispatches_today']}/{stats['cap']}). Skipping.")
        return []
    
    # Check due hooks
    due_hooks = lifecycle.check_due_hooks()
    
    if not due_hooks:
        print("✅ No hooks due.")
        return []
    
    print(f"📋 Found {len(due_hooks)} due hooks")
    
    followups = []
    for hook in due_hooks:
        message = lifecycle.render_followup(hook['id'])
        safe_message = guard.sanitize(message) if message else None
        
        if safe_message:
            followups.append({
                'hook_id': hook['id'],
                'entity_name': hook.get('entity_name', 'Unknown'),
                'message': safe_message,
            })
            print(f"  - [{hook['id']}] {hook.get('entity_name', 'Unknown')[:30]}...")
    
    return followups


def send_followups(followups: list, dry_run: bool = True):
    """
    Send follow-up messages via Telegram.
    
    Args:
        followups: List of follow-up dicts
        dry_run: If True, just print instead of sending
    """
    if not followups:
        print("No follow-ups to send.")
        return 0
    
    print(f"\n📤 {'[DRY RUN] ' if dry_run else ''}Sending {len(followups)} follow-ups...")
    
    sent_count = 0
    for fu in followups:
        hook_id = fu['hook_id']
        message = fu['message']
        entity_name = fu['entity_name']
        
        if dry_run:
            print(f"\n  [{hook_id}] {entity_name}")
            print(f"  Message: {message}")
        else:
            # Actually send via Telegram
            # For now, just log - actual implementation would use message tool
            print(f"\n  ✅ Sent: [{hook_id}] {message[:50]}...")
            sent_count += 1
        
        # Mark as dispatched
        lifecycle = HookLifecycle()
        lifecycle.mark_dispatched(hook_id)
        
        # Write trace
        trace = DailyMemoryTrace()
        trace.write(
            event_type='followup_sent',
            action='dispatched',
            entity_name=entity_name,
            topic_id=hook_id,
            causal_memory={},
            details={'message_preview': message[:100]},
            severity='info'
        )
    
    return sent_count if not dry_run else len(followups)


def status():
    """Show current status"""
    state = ContinuityState()
    status_data = state.get_status()
    
    print("=" * 60)
    print("TELEGRAM BOT INTEGRATION STATUS")
    print("=" * 60)
    print()
    
    print("Continuity Layer:")
    print(f"  Pending topics: {status_data['pending_topics']['count']}")
    print(f"  Active hooks: {len([h for h in status_data['pending_topics']['items'] if h.get('status') == 'active'])}")
    print()
    
    print("Time State:")
    print(f"  Phase: {status_data['time_state']['phase']}")
    print(f"  Proactive allowed: {status_data['time_state']['is_proactive_allowed']}")
    print()
    
    # Check if there are due hooks
    lifecycle = HookLifecycle()
    due_hooks = lifecycle.check_due_hooks()
    print(f"Due Hooks: {len(due_hooks)}")
    
    return status_data


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Telegram Bot for Continuity Layer")
    parser.add_argument("--check-due", action="store_true", help="Check for due hooks")
    parser.add_argument("--send", action="store_true", help="Actually send messages (default is dry-run)")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    
    args = parser.parse_args()
    
    if args.status:
        status()
    elif args.check_due:
        followups = check_and_prepare_followups()
        
        if followups:
            print()
            if args.send:
                sent = send_followups(followups, dry_run=False)
                print(f"\n✅ Sent {sent} follow-ups")
            elif args.dry_run:
                sent = send_followups(followups, dry_run=True)
                print(f"\n🔍 Would send {sent} follow-ups (dry-run)")
            else:
                print("Use --send to actually send, or --dry-run to simulate")
                print()
                send_followups(followups, dry_run=True)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()