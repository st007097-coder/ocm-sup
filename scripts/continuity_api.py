"""
Continuity Layer HTTP API
========================

Extends the Triple-Stream Search API with continuity layer endpoints.

Usage:
    python3 continuity_api.py [--port 5001]

Endpoints (continuity):
    GET  /continuity/status              - Continuity layer status
    GET  /continuity/pending             - Get pending topics
    POST /continuity/classify            - Classify a message
    GET  /continuity/carryover            - Get carryover context
    POST /continuity/set-pending         - Set a pending topic
    POST /continuity/resolve              - Resolve a pending topic
    GET  /continuity/hooks/due            - Check for due hooks
    POST /continuity/hooks/dispatch/<id> - Dispatch a hook

Endpoints (existing search):
    GET  /search?q=query&top_k=5        - Triple-Stream Search
    GET  /health                          - Health check
    GET  /stats                           - Search statistics
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add OCM Sup to path
sys.path.insert(0, '/root/.openclaw/workspace/OCM-Sup/scripts')

from flask import Flask, request, jsonify
from continuity.continuity_state import ContinuityState
from continuity.hook_lifecycle import HookLifecycle
from continuity.frontstage_guard import FrontstageGuard
from continuity.daily_memory_trace import DailyMemoryTrace

app = Flask(__name__)

# Global continuity instance
continuity = None


def init_continuity():
    """Initialize Continuity State"""
    global continuity
    continuity = ContinuityState()
    print("✅ Continuity Layer initialized")
    print(f"   Carryover enabled: {continuity.settings.get('carryover', {}).get('enabled', False)}")


# ============================================================
# Continuity Endpoints
# ============================================================

@app.route('/continuity/status')
def get_status():
    """Get continuity layer status"""
    try:
        status_data = continuity.get_status()
        return jsonify({
            'success': True,
            'data': status_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/pending')
def get_pending():
    """Get pending topics"""
    try:
        types = request.args.get('types', '').split(',') if request.args.get('types') else None
        limit = int(request.args.get('limit', 10))
        
        pending = continuity.get_pending_topics(types=types, limit=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'count': len(pending),
                'items': pending[:limit]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/classify', methods=['POST'])
def classify_message():
    """Classify a message"""
    try:
        data = request.get_json() or {}
        user_text = data.get('text', '')
        is_new_session = data.get('is_new_session', False)
        
        if not user_text:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        result = continuity.handle_message(
            user_text=user_text,
            is_new_session=is_new_session
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/carryover')
def get_carryover():
    """Get carryover context for /new sessions"""
    try:
        user_text = request.args.get('text', '')
        is_new_session = request.args.get('is_new_session', 'true').lower() == 'true'
        
        context = continuity.build_runtime_context(
            is_new_session=is_new_session,
            user_text=user_text
        )
        
        return jsonify({
            'success': True,
            'data': context
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/set-pending', methods=['POST'])
def set_pending():
    """Set a pending topic"""
    try:
        data = request.get_json() or {}
        
        entity_name = data.get('entity_name')
        event_type = data.get('event_type', 'parked_topic')
        topic_id = data.get('topic_id')
        followup_focus = data.get('followup_focus')
        causal_memory = data.get('causal_memory', {})
        
        if not entity_name:
            return jsonify({
                'success': False,
                'error': 'No entity_name provided'
            }), 400
        
        if topic_id:
            # Update existing
            continuity.carryover.set_pending_topic(
                topic_id=topic_id,
                entity_name=entity_name,
                event_type=event_type,
                followup_focus=followup_focus,
                causal_memory=causal_memory
            )
        else:
            # Create new - get from last classification
            pass
        
        return jsonify({
            'success': True,
            'data': {
                'entity_name': entity_name,
                'event_type': event_type
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/resolve', methods=['POST'])
def resolve_pending():
    """Resolve a pending topic"""
    try:
        data = request.get_json() or {}
        
        topic_id = data.get('topic_id')
        reason = data.get('reason', 'resolved')
        
        result = continuity.resolve_pending_topic(
            topic_id=topic_id,
            reason=reason
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/hooks/due')
def get_due_hooks():
    """Check for due hooks"""
    try:
        lifecycle = HookLifecycle()
        
        # Apply sleep suppress
        lifecycle.check_and_apply_sleep_suppress()
        
        # Check due hooks
        due_hooks = lifecycle.check_due_hooks()
        
        # Sanitize messages
        guard = FrontstageGuard()
        for hook in due_hooks:
            message = lifecycle.render_followup(hook['id'])
            hook['rendered_message'] = guard.sanitize(message) if message else None
        
        return jsonify({
            'success': True,
            'data': {
                'count': len(due_hooks),
                'hooks': due_hooks
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/hooks/dispatch/<hook_id>', methods=['POST'])
def dispatch_hook(hook_id):
    """Dispatch a hook (mark as sent)"""
    try:
        lifecycle = HookLifecycle()
        
        hook = lifecycle.get_hook(hook_id)
        if not hook:
            return jsonify({
                'success': False,
                'error': f'Hook not found: {hook_id}'
            }), 404
        
        lifecycle.mark_dispatched(hook_id)
        
        # Write trace
        trace = DailyMemoryTrace()
        trace.write(
            event_type=hook.get('event_type', 'unknown'),
            action='dispatched',
            entity_name=hook.get('entity_name', 'Unknown'),
            topic_id=hook_id,
            causal_memory=hook.get('causal_memory', {}),
            severity='info'
        )
        
        return jsonify({
            'success': True,
            'data': {
                'hook_id': hook_id,
                'status': 'dispatched'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/hooks/close/<hook_id>', methods=['POST'])
def close_hook(hook_id):
    """Close a hook"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'resolved')
        
        lifecycle = HookLifecycle()
        lifecycle.close_hook(hook_id, reason)
        
        return jsonify({
            'success': True,
            'data': {
                'hook_id': hook_id,
                'status': 'closed',
                'reason': reason
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/continuity/traces/today')
def get_today_traces():
    """Get today's memory traces"""
    try:
        event_type = request.args.get('event_type')
        
        trace = DailyMemoryTrace()
        traces = trace.get_today_traces(event_type=event_type)
        
        return jsonify({
            'success': True,
            'data': {
                'count': len(traces),
                'traces': traces
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Standard Endpoints (for reference)
# ============================================================

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'OCM Sup Continuity API'
    })


# ============================================================
# Main
# ============================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Continuity Layer HTTP API")
    parser.add_argument('--port', type=int, default=5001, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OCM SUP CONTINUITY API")
    print("=" * 60)
    print()
    
    # Initialize continuity
    init_continuity()
    
    print()
    print(f"Starting API on {args.host}:{args.port}")
    print()
    print("Endpoints:")
    print("  GET  /continuity/status          - Status")
    print("  GET  /continuity/pending          - Pending topics")
    print("  POST /continuity/classify         - Classify message")
    print("  GET  /continuity/carryover        - Carryover context")
    print("  POST /continuity/set-pending      - Set pending topic")
    print("  POST /continuity/resolve          - Resolve pending")
    print("  GET  /continuity/hooks/due         - Due hooks")
    print("  POST /continuity/hooks/dispatch/<id> - Dispatch hook")
    print("  POST /continuity/hooks/close/<id>   - Close hook")
    print("  GET  /continuity/traces/today     - Today's traces")
    print()
    print("=" * 60)
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
