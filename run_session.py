
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# directory containing analyzer.py and destinations.txt
PROJECT_DIR = Path(__file__).resolve().parent

# number of analyzer runs per operating system
REPETITIONS = 3

# ------------------------------------------------------------
# Function: run_session
#
# Purpose: Run the analyzer.py script for each operating system for 
# the specified number of repetitions, and save the results to the results/logs/ directory.
#
# Parameters: None
#
# Returns: None
#
# ------------------------------------------------------------
def run_session():
    # this script is intended to run from Windows
    if os.name != "nt":
        print("Run this script using Windows Python, not WSL Python.")
        return

    # convert C:\path\to\project into /mnt/c/path/to/project for WSL
    drive = PROJECT_DIR.drive[0].lower()
    relative_path = PROJECT_DIR.relative_to(PROJECT_DIR.anchor)
    wsl_dir = f"/mnt/{drive}/" + relative_path.as_posix()

    # directory for individual execution logs
    log_dir = PROJECT_DIR / "results" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # execute all runs for each operating system
    for system in ("windows", "linux"):
        for repetition in range(1, REPETITIONS + 1):

            if system == "windows":
                command = [sys.executable, "analyzer.py"]
            else:
                command = [
                    "wsl.exe",
                    "--cd", wsl_dir,
                    "--exec", "python3", "analyzer.py"
                ]

            log_file = log_dir / (
                f"{session_id}_{system}_run{repetition}.log"
            )

            print(
                f"Starting {system} run "
                f"{repetition}/{REPETITIONS}...",
                flush=True
            )

            try:
                with open(log_file, "w", encoding="utf-8") as log:
                    result = subprocess.run(
                        command,
                        cwd=PROJECT_DIR,
                        stdout=log,
                        stderr=subprocess.STDOUT
                    )

                if result.returncode == 0:
                    print(f"Finished: {log_file.name}", flush=True)
                else:
                    print(
                        f"Execution failed (exit {result.returncode}): "
                        f"{log_file.name}",
                        flush=True
                    )

            except OSError as error:
                print(f"Could not start {system}: {error}", flush=True)


if __name__ == "__main__":
    run_session()
