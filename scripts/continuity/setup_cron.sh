#!/bin/bash
#
# OCM Sup Continuity Layer — Cron Setup Script
#
# Usage:
#   ./setup_cron.sh                    # Show current setup status
#   ./setup_cron.sh --install          # Install cron job
#   ./setup_cron.sh --uninstall        # Remove cron job
#   ./setup_cron.sh --test             # Test the check-due script
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTINUITY_DIR="$SCRIPT_DIR/continuity"
VENV_BIN="$HOME/.openclaw/venv/bin"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

echo_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

echo_info() {
    echo -e "${YELLOW}INFO: $1${NC}"
}

# Check prerequisites
check_prereqs() {
    echo "Checking prerequisites..."
    
    # Check venv
    if [ ! -f "$VENV_BIN/python3" ]; then
        echo_error "Python venv not found at $VENV_BIN"
        return 1
    fi
    echo_success "Python venv found"
    
    # Check continuity module
    if [ ! -f "$CONTINUITY_DIR/continuity_state.py" ]; then
        echo_error "Continuity module not found at $CONTINUITY_DIR"
        return 1
    fi
    echo_success "Continuity module found"
    
    # Check smart_recall script
    if [ ! -f "$CONTINUITY_DIR/smart_recall_carryover.py" ]; then
        echo_error "smart_recall_carryover.py not found"
        return 1
    fi
    echo_success "smart_recall_carryover.py found"
    
    echo ""
}

# Test the check-due script
test_check_due() {
    echo "Testing smart_recall_carryover.py --check-due..."
    echo ""
    
    cd "$SCRIPT_DIR"
    $VENV_BIN/python3 scripts/continuity/smart_recall_carryover.py --check-due 2>&1 || {
        echo_error "Test failed"
        return 1
    }
    
    echo_success "Test completed"
}

# Show status
show_status() {
    echo ""
    echo "============================================================"
    echo "OCM SUP CONTINUITY LAYER — CRON STATUS"
    echo "============================================================"
    echo ""
    
    # Show current openclaw cron jobs (if gateway is available)
    echo "Current OpenClaw cron jobs:"
    echo "----------------------------"
    openclaw cron list 2>&1 || echo "(Gateway not connected - cannot list crons)"
    echo ""
    
    # Check if our cron would work
    echo "Continuity Layer:"
    echo "-----------------"
    $VENV_BIN/python3 $CONTINUITY_DIR/smart_recall_carryover.py --status 2>&1 | head -20
    
    echo ""
}

# Install cron job
install_cron() {
    echo "This script will help you set up the continuity layer cron."
    echo ""
    echo "Options:"
    echo ""
    echo "1. Direct cron (requires gateway access)"
    echo "   - Runs every 2 hours via openclaw cron"
    echo "   - Checks for due hooks and logs results"
    echo "   - No automatic announcement (just logging)"
    echo ""
    echo "2. Manual setup"
    echo "   - Creates a launcher script"
    echo "   - You add to system crontab yourself"
    echo ""
    echo "Which option do you want? (1/2): "
    read -r option
    
    case $option in
        1)
            install_openclaw_cron
            ;;
        2)
            install_manual_cron
            ;;
        *)
            echo_error "Invalid option"
            return 1
            ;;
    esac
}

install_openclaw_cron() {
    echo ""
    echo_info "Installing OpenClaw cron job..."
    echo ""
    
    # Create a script that will be called by the cron
    cat > "$CONTINUITY_DIR/run_check_due.sh" << 'SCRIPT'
#!/bin/bash
# Run the smart recall check
cd "$(dirname "$0")"
/root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --check-due >> /tmp/continuity_cron.log 2>&1
SCRIPT
    chmod +x "$CONTINUITY_DIR/run_check_due.sh"
    
    # Try to add via openclaw
    openclaw cron add \
        --every "2h" \
        --description "OCM Sup Continuity Layer - Check due hooks" \
        --light-context \
        --disabled 2>&1 || {
        echo_error "Failed to add cron via openclaw. Gateway may not be connected."
        echo_info "Manual setup:"
        echo "  1. Connect to gateway"
        echo "  2. Run: openclaw cron add --every 2h --description 'Continuity check'"
        echo ""
        echo "Or use option 2 (manual cron) instead."
        return 1
    }
    
    echo_success "Cron job installed via OpenClaw"
}

install_manual_cron() {
    echo ""
    echo_info "Creating manual cron script..."
    echo ""
    
    # Create the launcher script
    cat > "$CONTINUITY_DIR/run_check_due.sh" << 'SCRIPT'
#!/bin/bash
# OCM Sup Continuity Layer - Check Due Hooks
# This script is called by system cron

LOG_FILE="/tmp/continuity_check_due.log"
ERROR_LOG="/tmp/continuity_check_due.error.log"

cd "/root/.openclaw/workspace/OCM-Sup"

{
    echo "============================================================"
    echo "Continuity Check - $(date)"
    echo "============================================================"
    
    /root/.openclaw/venv/bin/python3 scripts/continuity/smart_recall_carryover.py --check-due
    
    echo ""
} >> "$LOG_FILE" 2>> "$ERROR_LOG"
SCRIPT
    chmod +x "$CONTINUITY_DIR/run_check_due.sh"
    
    echo_success "Cron script created at: $CONTINUITY_DIR/run_check_due.sh"
    echo ""
    echo "To add to system cron (as root or via crontab -e):"
    echo ""
    echo "  # Check due hooks every 2 hours"
    echo "  0 */2 * * * /root/.openclaw/workspace/OCM-Sup/scripts/continuity/run_check_due.sh"
    echo ""
    echo "Or for testing, every 30 minutes:"
    echo "  */30 * * * * /root/.openclaw/workspace/OCM-Sup/scripts/continuity/run_check_due.sh"
    echo ""
}

# Uninstall cron
uninstall_cron() {
    echo_info "Removing cron job..."
    echo ""
    
    # Remove the run script
    if [ -f "$CONTINUITY_DIR/run_check_due.sh" ]; then
        rm -f "$CONTINUITY_DIR/run_check_due.sh"
        echo_success "Removed run script"
    fi
    
    # Try to remove via openclaw
    openclaw cron list 2>&1 | grep -i continuity | awk '{print $1}' | while read -r id; do
        echo_info "Would delete cron: $id"
    done || true
    
    echo ""
    echo_info "Note: OpenClaw cron jobs must be removed via 'openclaw cron delete <id>'"
    echo_info "Run 'openclaw cron list' to see current jobs"
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
        check_prereqs && test_check_due
        ;;
    *)
        show_status
        echo "Usage: $0 [--install|--uninstall|--test]"
        ;;
esac