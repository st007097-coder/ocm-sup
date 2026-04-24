#!/bin/bash
#
# OCM Sup Continuity Layer — Telegram Bot Setup Script
#
# Usage:
#   ./setup_telegram.sh              # Show status
#   ./setup_telegram.sh --install    # Install notification cron
#   ./setup_telegram.sh --test       # Test notifications
#   ./setup_telegram.sh --uninstall  # Remove notification cron
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTINUITY_DIR="$SCRIPT_DIR"
VENV_BIN="$HOME/.openclaw/venv/bin"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_error() { echo -e "${RED}ERROR: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
echo_info() { echo -e "${YELLOW}INFO: $1${NC}"; }

# Check prerequisites
check_prereqs() {
    echo "Checking prerequisites..."
    
    # Check venv
    if [ ! -f "$VENV_BIN/python3" ]; then
        echo_error "Python venv not found at $VENV_BIN"
        return 1
    fi
    echo_success "Python venv found"
    
    # Check telegram_notify script
    if [ ! -f "$CONTINUITY_DIR/telegram_notify.py" ]; then
        echo_error "telegram_notify.py not found"
        return 1
    fi
    echo_success "telegram_notify.py found"
    
    echo ""
}

# Test notifications
test_notify() {
    echo "Testing telegram_notify.py --check-due --dry-run..."
    echo ""
    
    cd "$SCRIPT_DIR"
    $VENV_BIN/python3 telegram_notify.py --check-due --dry-run 2>&1 || {
        echo_error "Test failed"
        return 1
    }
    
    echo_success "Test completed"
}

# Show status
show_status() {
    echo ""
    echo "============================================================"
    echo "TELEGRAM BOT INTEGRATION STATUS"
    echo "============================================================"
    echo ""
    
    cd "$SCRIPT_DIR"
    $VENV_BIN/python3 telegram_notify.py --status 2>&1
    
    echo ""
    echo_info "To set up Telegram notifications:"
    echo "  1. Ensure OpenClaw Telegram plugin is configured"
    echo "  2. The bot will use OpenClaw's message system to send"
    echo "  3. Configure proactive chat settings in settings.json"
    echo ""
}

# Install notification cron
install_cron() {
    echo_info "Installing Telegram notification cron..."
    echo ""
    
    # Create the launcher script
    cat > "$CONTINUITY_DIR/run_telegram_notify.sh" << 'SCRIPT'
#!/bin/bash
# OCM Sup Continuity Layer - Telegram Notifications
# Checks for due hooks and sends follow-ups via OpenClaw

cd "/root/.openclaw/workspace/OCM-Sup/scripts/continuity"

/root/.openclaw/venv/bin/python3 telegram_notify.py --check-due --send >> /tmp/continuity_telegram.log 2>&1
SCRIPT
    chmod +x "$CONTINUITY_DIR/run_telegram_notify.sh"
    
    echo_success "Notification script created"
    echo ""
    echo_info "To add to system cron (crontab -e):"
    echo ""
    echo "  # Send follow-ups every 2 hours during active hours"
    echo "  0 */2 * * * /root/.openclaw/workspace/OCM-Sup/scripts/continuity/run_telegram_notify.sh"
    echo ""
    echo "Or for testing, every 30 minutes:"
    echo "  */30 * * * * /root/.openclaw/workspace/OCM-Sup/scripts/continuity/run_telegram_notify.sh"
    echo ""
    echo_info "Note: Ensure proactive_chat.enabled=true in settings.json"
    echo_info "and sleep_time/wake_time are correctly set."
}

# Uninstall
uninstall_cron() {
    echo_info "Removing notification cron..."
    
    if [ -f "$CONTINUITY_DIR/run_telegram_notify.sh" ]; then
        rm -f "$CONTINUITY_DIR/run_telegram_notify.sh"
        echo_success "Removed notification script"
    fi
    
    echo_info "Remember to also remove the crontab entry (crontab -e)"
}

# Main
case "${1:-}" in
    --install)
        check_prereqs && install_cron
        ;;
    --uninstall)
        uninstall_cron
        ;;
    --test)
        check_prereqs && test_notify
        ;;
    *)
        show_status
        echo "Usage: $0 [--install|--uninstall|--test]"
        ;;
esac