# =========================================================
# RUN ALL (AUTOMATED ORCHESTRATOR)
# Chains: PIB scrape -> CA scrape -> Telegram pipeline
# Run this on a schedule (see setup_auto.ps1)
# =========================================================

import subprocess
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))


def run_step(script_name):
    path = os.path.join(BASE, script_name)
    print("\n" + "=" * 50)
    print("STEP: %s" % script_name)
    print("=" * 50)
    try:
        result = subprocess.run(
            [sys.executable, path],
            cwd=BASE,
            check=False,
        )
        if result.returncode != 0:
            print("WARN: %s exited with code %d" % (script_name, result.returncode))
        return result.returncode
    except Exception as e:
        print("ERROR running %s: %s" % (script_name, e))
        return 1


if __name__ == "__main__":
    print("HARRIT AUTOMATED PIPELINE STARTED")
    # 1. Refresh PIB data from pib.gov.in
    run_step("pib_scraper.py")
    # 2. Refresh GKToday / Vision IAS / Insights IAS / Drishti IAS
    run_step("current_affairs_scraper.py")
    # 3. Merge, dedup, filter, send to Telegram
    run_step("run_pipeline.py")
    # 4. Auto-pick today's Utkarsh YouTube CA video -> transcript -> translate -> send
    run_step("utkarsh_youtube_ca.py")
    print("\nHARRIT AUTOMATED PIPELINE FINISHED")
