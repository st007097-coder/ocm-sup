"""
Continuity Layer Integration Test
================================

Comprehensive test of all continuity modules working together.

Tests the full flow:
1. Message classification
2. Staged/tracked item creation
3. Carryover management
4. Hook lifecycle
5. Frontstage guard
6. Daily memory traces
7. Graph integration (if available)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from continuity.state_router import StateRouter, RoutingType
from continuity.carryover import CarryoverManager
from continuity.continuity_state import ContinuityState
from continuity.hook_lifecycle import HookLifecycle
from continuity.frontstage_guard import FrontstageGuard
from continuity.daily_memory_trace import DailyMemoryTrace


def test_message_classification(state: ContinuityState):
    """Test 1: Message Classification"""
    print("=" * 60)
    print("TEST 1: Message Classification")
    print("=" * 60)
    
    test_cases = [
        # (message, expected_routing, expected_event_type)
        ("幫我記住我哋研究緊OCM Sup融合方案", "tracked_followup", "delegated_task"),
        ("麻煩你幫我跟進古洞站項目進度", "tracked_followup", "delegated_task"),
        ("我感覺有啲攰", "tracked_followup", "watchful_state"),
        ("呢個係私人資料，保密", "tracked_followup", "sensitive_event"),
        ("你好嗎？", "casual_chat", None),
        ("我哋之前研究緊融合方案，繼續傾", "casual_chat", None),
    ]
    
    passed = 0
    failed = 0
    
    for message, expected_routing, expected_event_type in test_cases:
        result = state.handle_message(message)
        routing = result["classification"]["routing"]
        event_type = result["classification"]["event_type"]
        
        routing_ok = routing == expected_routing
        event_ok = event_type == expected_event_type
        
        if routing_ok and event_ok:
            print(f"✅ PASS: '{message[:30]}...'")
            print(f"   Routing: {routing} (expected {expected_routing})")
            print(f"   Event: {event_type} (expected {expected_event_type})")
            passed += 1
        else:
            print(f"❌ FAIL: '{message[:30]}...'")
            print(f"   Routing: {routing} (expected {expected_routing})")
            print(f"   Event: {event_type} (expected {expected_event_type})")
            failed += 1
        print()
    
    print(f"\nClassification Results: {passed}/{passed+failed} passed")
    return passed, failed


def test_carryover(state: ContinuityState):
    """Test 2: Carryover Management"""
    print("=" * 60)
    print("TEST 2: Carryover Management")
    print("=" * 60)
    
    # Simulate conversation
    state.handle_message("我哋研究緊OCM Sup融合方案")
    state.handle_message("好主意！研究下點融合。")
    state.handle_message("幫我記住呢個主題")
    
    # Check carryover
    carryover_context = state.carryover.get_pending_topic()
    
    print(f"Pending topic: {carryover_context.get('entity_name') if carryover_context else 'None'}")
    print(f"Event type: {carryover_context.get('event_type') if carryover_context else 'None'}")
    
    # Test /new session
    new_context = state.build_runtime_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    
    print(f"\n/new Session Context:")
    print(f"  Type: {new_context['type']}")
    print(f"  Has continuity prompt: {bool(new_context.get('continuity_prompt'))}")
    print(f"  Is low-info greeting: {new_context['is_low_info_greeting']}")
    print(f"  Continuity prompt: {new_context.get('continuity_prompt', 'N/A')}")
    
    # Check if it correctly identified low-info greeting
    if new_context['is_low_info_greeting'] and new_context.get('continuity_prompt'):
        print("\n✅ PASS: Carryover with low-info greeting")
        return 1, 0
    else:
        print("\n❌ FAIL: Carryover not working correctly")
        return 0, 1


def test_hook_lifecycle(state: ContinuityState):
    """Test 3: Hook Lifecycle"""
    print("=" * 60)
    print("TEST 3: Hook Lifecycle")
    print("=" * 60)
    
    lifecycle = state.router._init_state_files()
    lifecycle = HookLifecycle()
    
    # Create an incident first
    incident_id = state.router.write_tracked_incident(
        state.handle_message("麻煩你幫我跟進古洞站項目進度")["classification"]
    )
    
    # Create a hook
    hook_id = lifecycle.create_hook(
        incident_id=incident_id,
        entity_name="古洞站項目進度",
        event_type="delegated_task",
        followup_focus="檢查項目進度",
        causal_memory={
            "facts": ["古洞站項目", "QS工作"],
            "state": "delegated",
            "time_anchor": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    
    print(f"Created hook: {hook_id}")
    
    # Check if hook is due
    due_hooks = lifecycle.check_due_hooks()
    print(f"Due hooks: {len(due_hooks)}")
    
    # Render followup
    if due_hooks:
        message = lifecycle.render_followup(due_hooks[0]["id"])
        print(f"Followup message: {message}")
    
    # Test frontstage guard on the message
    guard = FrontstageGuard()
    if due_hooks:
        safe_message = guard.sanitize(message)
        print(f"Sanitized message: {safe_message}")
    
    # Mark as dispatched
    lifecycle.mark_dispatched(hook_id)
    
    # Check dispatch stats
    stats = lifecycle.get_dispatch_stats()
    print(f"Dispatch stats: {stats}")
    
    # Close the hook
    lifecycle.close_hook(hook_id, "resolved")
    
    # Verify closed
    closed_hook = lifecycle.get_hook(hook_id)
    print(f"Hook status after close: {closed_hook['status']}")
    
    if closed_hook and closed_hook["status"] == "closed":
        print("\n✅ PASS: Hook lifecycle working")
        return 1, 0
    else:
        print("\n❌ FAIL: Hook lifecycle issue")
        return 0, 1


def test_daily_memory_traces(state: ContinuityState):
    """Test 4: Daily Memory Traces"""
    print("=" * 60)
    print("TEST 4: Daily Memory Traces")
    print("=" * 60)
    
    trace = DailyMemoryTrace()
    
    # Write a trace
    path = trace.write(
        event_type="parked_topic",
        action="created",
        entity_name="整合測試主題",
        topic_id="test_integration_001",
        causal_memory={
            "facts": ["整合測試"],
            "state": "active",
            "time_anchor": datetime.now().isoformat(),
        },
        severity="created"
    )
    
    print(f"Written to: {path}")
    
    # Get today's traces
    traces = trace.get_today_traces()
    print(f"Today's traces: {len(traces)}")
    
    # Search by topic
    results = trace.get_traces_by_topic("整合測試")
    print(f"Found traces for '整合測試': {len(results)}")
    
    # Weekly summary
    summary = trace.get_weekly_summary()
    print(f"Weekly summary: {summary['total_traces']} traces")
    
    if len(traces) > 0 and len(results) > 0:
        print("\n✅ PASS: Daily memory traces working")
        return 1, 0
    else:
        print("\n❌ FAIL: Daily memory traces issue")
        return 0, 1


def test_frontstage_guard():
    """Test 5: Frontstage Guard"""
    print("=" * 60)
    print("TEST 5: Frontstage Guard")
    print("=" * 60)
    
    guard = FrontstageGuard()
    
    test_cases = [
        # (message, should_be_safe)
        ("你好嗎？想傾乜？", True),
        ("你之前提到嘅古洞站項目進度點樣？", True),
        ("想提醒你之前交代嘅任務（上次傾呢個係 2026-04-24T14:00:00.123456）", False),
        ("你之前提到 hook_12345678，想繼續傾嗎？", False),
        ("關於 incident_abcdefgh 呢個跟進事項", False),
    ]
    
    passed = 0
    failed = 0
    
    for message, should_be_safe in test_cases:
        is_safe = guard.is_safe(message)
        sanitized = guard.sanitize(message) if not is_safe else message
        
        if is_safe == should_be_safe:
            print(f"✅ PASS: '{message[:40]}...'")
            print(f"   is_safe={is_safe}, expected={should_be_safe}")
            passed += 1
        else:
            print(f"❌ FAIL: '{message[:40]}...'")
            print(f"   is_safe={is_safe}, expected={should_be_safe}")
            failed += 1
        
        if not is_safe:
            print(f"   Sanitized: {sanitized[:60]}...")
        print()
    
    # Test guard context
    context = guard.build_guard_context()
    print(f"Guard context length: {len(context)} chars")
    
    stats = guard.get_stats()
    print(f"Guard stats: {stats}")
    
    print(f"\nFrontstage Guard Results: {passed}/{passed+failed} passed")
    return passed, failed


def test_full_conversation_flow():
    """Test 6: Full Conversation Flow"""
    print("=" * 60)
    print("TEST 6: Full Conversation Flow")
    print("=" * 60)
    
    state = ContinuityState()
    
    # Step 1: User mentions a topic
    print("Step 1: User mentions a topic...")
    result = state.handle_message("我哋研究緊OCM Sup同openclaw-continuity融合方案")
    print(f"  Classification: {result['classification']['routing']}")
    
    # Step 2: User parks it for later
    print("Step 2: User parks it...")
    result = state.handle_message("幫我記住呢個研究主題，遲啲再傾")
    print(f"  Classification: {result['classification']['routing']}")
    print(f"  Action: {result['actions']}")
    
    pending = state.carryover.get_pending_topic()
    print(f"  Pending topic: {pending.get('entity_name') if pending else 'None'}")
    
    # Step 3: User does /new
    print("Step 3: User does /new...")
    context = state.build_runtime_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    print(f"  Continuation prompt: {context.get('continuity_prompt', 'None')}")
    
    # Step 4: Assistant responds and follows up later
    print("Step 4: Assistant follows up...")
    state.handle_message("早晨！我記得你之前話想研究融合方案，準備好繼續未？")
    
    # Step 5: Check if hook was created
    hooks = state.router.get_pending_topics(types=["delegated_task"])
    print(f"  Pending hooks: {len(hooks)}")
    
    # Step 6: Resolve the topic
    print("Step 6: User resolves the topic...")
    result = state.resolve_pending_topic(reason="resolved")
    print(f"  Resolve result: {result}")
    
    # Step 7: Verify carryover is cleared
    pending_after = state.carryover.get_pending_topic()
    print(f"  Pending after resolve: {pending_after}")
    
    if pending_after is None:
        print("\n✅ PASS: Full conversation flow working")
        return 1, 0
    else:
        print("\n❌ FAIL: Full conversation flow issue")
        return 0, 1


def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("OCM SUP CONTINUITY LAYER — INTEGRATION TEST")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize state
    state = ContinuityState()
    
    # Run tests
    total_passed = 0
    total_failed = 0
    
    # Test 1: Message Classification
    p, f = test_message_classification(state)
    total_passed += p
    total_failed += f
    
    # Test 2: Carryover
    p, f = test_carryover(state)
    total_passed += p
    total_failed += f
    
    # Test 3: Hook Lifecycle
    p, f = test_hook_lifecycle(state)
    total_passed += p
    total_failed += f
    
    # Test 4: Daily Memory Traces
    p, f = test_daily_memory_traces(state)
    total_passed += p
    total_failed += f
    
    # Test 5: Frontstage Guard
    p, f = test_frontstage_guard()
    total_passed += p
    total_failed += f
    
    # Test 6: Full Conversation Flow
    p, f = test_full_conversation_flow()
    total_passed += p
    total_failed += f
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Total passed: {total_passed}")
    print(f"Total failed: {total_failed}")
    print(f"Success rate: {total_passed}/{total_passed+total_failed} ({100*total_passed/(total_passed+total_failed):.1f}%)")
    print()
    
    if total_failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️ {total_failed} TESTS FAILED")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
