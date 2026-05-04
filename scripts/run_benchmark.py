#!/usr/bin/env python3
"""Run benchmark in isolated subprocess"""
import subprocess
import sys

# Run the benchmark script as subprocess
result = subprocess.run(
    [sys.executable, '/home/jacky/.openclaw/workspace/OCM-Sup/scripts/silent_benchmark.py'],
    capture_output=True,
    text=True,
    timeout=300
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
print("Return code:", result.returncode)