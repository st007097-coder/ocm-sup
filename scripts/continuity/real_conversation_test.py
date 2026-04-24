"""
Continuity Layer — Real Conversation Test
=========================================

This module provides a test framework for testing the continuity layer
in a simulated real conversation flow.

Usage:
    python3 real_conversation_test.py
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from continuity.continuity_state import ContinuityState


def simulate_user_says(state: ContinuityState, message: str):
    """Simulate a user message and print the result"""
    print(f"\n👤 USER: {message}")
    result = state.handle_message(message)
    print(f"   Routing: {result['classification']['routing']}")
    print(f"   Event: {result['classification']['event_type']}")
    entity = result['classification'].get('entity_name') or 'N/A'
    print(f"   Entity: {entity[:50]}")
    if result['actions']:
        print(f"   Actions: {[a['action'] for a in result['actions']]}")
    return result


def simulate_new_session(state: ContinuityState, message: str):
    """Simulate a /new session"""
    print(f"\n🔄 /new SESSION: {message}")
    context = state.build_runtime_context(
        is_new_session=True,
        user_text=message,
        agent_persona="阿星"
    )
    print(f"   Type: {context['type']}")
    print(f"   Continuation prompt: {context.get('continuity_prompt', 'None')}")
    print(f"   Is low-info greeting: {context['is_low_info_greeting']}")
    return context


def test_basic_classification():
    """Test 1: Basic message classification"""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Message Classification")
    print("=" * 60)
    
    state = ContinuityState()
    
    test_cases = [
        ("你好嗎？", "casual_chat", None),
        ("幫我記住我哋研究緊OCM Sup", "tracked_followup", "delegated_task"),
        ("麻煩你幫我跟進古洞站項目", "tracked_followup", "delegated_task"),
        ("我感覺有啲攰", "tracked_followup", "watchful_state"),
    ]
    
    passed = 0
    for message, expected_routing, expected_event in test_cases:
        result = simulate_user_says(state, message)
        routing = result['classification']['routing']
        event = result['classification']['event_type']
        
        if routing == expected_routing and event == expected_event:
            print(f"   ✅ PASS")
            passed += 1
        else:
            print(f"   ❌ FAIL (expected {expected_routing}/{expected_event})")
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_carryover_flow():
    """Test 2: Carryover flow"""
    print("\n" + "=" * 60)
    print("TEST 2: Carryover Flow")
    print("=" * 60)
    
    state = ContinuityState()
    
    # User mentions something important
    print("\n--- Phase 1: User parks a topic ---")
    simulate_user_says(state, "我哋研究緊OCM Sup同openclaw-continuity融合方案")
    simulate_user_says(state, "幫我記住呢個，遲啲再傾")
    
    # Check pending topic
    pending = state.carryover.get_pending_topic()
    print(f"\n📌 Pending topic: {pending.get('entity_name') if pending else 'None'}")
    
    # User does /new
    print("\n--- Phase 2: User does /new ---")
    context = simulate_new_session(state, "早晨")
    
    if context.get('continuity_prompt') and 'OCM Sup' in context['continuity_prompt']:
        print("   ✅ PASS: Carryover works")
        return True
    else:
        print("   ❌ FAIL: Carryover not working")
        return False


def test_full_conversation():
    """Test 3: Full conversation with follow-up"""
    print("\n" + "=" * 60)
    print("TEST 3: Full Conversation with Follow-up")
    print("=" * 60)
    
    state = ContinuityState()
    
    print("\n--- Turn 1 ---")
    simulate_user_says(state, "我哋研究緊OCM Sup融合方案")
    
    print("\n--- Turn 2 ---")
    result = simulate_user_says(state, "幫我記住呢個研究主題")
    
    print("\n--- Turn 3: /new session ---")
    context = state.build_runtime_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    print(f"   Continuation: {context.get('continuity_prompt', 'None')}")
    
    print("\n--- Turn 4: Assistant follows up ---")
    simulate_user_says(state, "我記得你之前話想繼續研究融合方案，準備好未？")
    
    print("\n--- Turn 5: User resolves ---")
    result = state.resolve_pending_topic(reason="resolved")
    print(f"   Resolved: {result['resolved']}")
    
    # Check carryover cleared
    pending_after = state.carryover.get_pending_topic()
    if pending_after is None:
        print("   ✅ PASS: Topic resolved and carryover cleared")
        return True
    else:
        print("   ❌ FAIL: Carryover not cleared")
        return False


def test_watchful_state():
    """Test 4: Watchful state"""
    print("\n" + "=" * 60)
    print("TEST 4: Watchful State (Health Monitor)")
    print("=" * 60)
    
    state = ContinuityState()
    
    print("\n--- User mentions health concern ---")
    result = simulate_user_says(state, "我感覺有啲頭疼")
    
    print("\n--- /new session to check ---")
    context = state.build_runtime_context(
        is_new_session=True,
        user_text="早晨",
        agent_persona="阿星"
    )
    print(f"   Continuation: {context.get('continuity_prompt', 'None')}")
    
    # Check it's classified as watchful_state
    if result['classification']['event_type'] == 'watchful_state':
        print("   ✅ PASS: Correctly classified as watchful_state")
        return True
    else:
        print("   ❌ FAIL: Not classified as watchful_state")
        return False


def test_sensitive_event():
    """Test 5: Sensitive event"""
    print("\n" + "=" * 60)
    print("TEST 5: Sensitive Event (Confidential)")
    print("=" * 60)
    
    state = ContinuityState()
    
    print("\n--- User mentions sensitive topic ---")
    result = simulate_user_says(state, "呢個係私人資料，唔好話俾其他人知")
    
    if result['classification']['event_type'] == 'sensitive_event':
        print("   ✅ PASS: Correctly classified as sensitive_event")
        return True
    else:
        print("   ❌ FAIL: Not classified as sensitive_event")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OCM SUP CONTINUITY LAYER — REAL CONVERSATION TEST")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Run tests
    results.append(("Basic Classification", test_basic_classification()))
    results.append(("Carryover Flow", test_carryover_flow()))
    results.append(("Full Conversation", test_full_conversation()))
    results.append(("Watchful State", test_watchful_state()))
    results.append(("Sensitive Event", test_sensitive_event()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED")
    
    print("=" * 60)


if __name__ == "__main__":
    main()