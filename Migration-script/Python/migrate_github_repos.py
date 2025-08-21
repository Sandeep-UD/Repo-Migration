import os
import csv
import subprocess
from datetime import datetime
from dotenv import load_dotenv

LOG_FILE = "MigrationLog.txt"
OUTPUT_CSV = "MigrationDetails.csv"
LOGS_DIR = "logs"
CSV_FILE = "repos.csv"
ENV_FILE = ".env"

def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# Load .env
if not os.path.exists(ENV_FILE):
    log_message(".env file not found.", "ERROR")
    exit(1)
load_dotenv(ENV_FILE)
GH_SOURCE_PAT = os.getenv("GH_PAT")
GH_PAT = os.getenv("TARGET_GH_PAT")
SOURCE = os.getenv("GH_ORG")
DESTINATION = os.getenv("TARGET_GH_ORG")

if not all([GH_SOURCE_PAT, GH_PAT, SOURCE, DESTINATION]):
    log_message("Required environment variables missing. Ensure GH_SOURCE_PAT, GH_PAT, SOURCE, DESTINATION are set in .env file.", "ERROR")
    exit(1)

# Prepare logs dir and log file
os.makedirs(LOGS_DIR, exist_ok=True)
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Migration Log - {datetime.now()}\n")

# Prepare output CSV
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "SourceOrg", "SourceRepo", "TargetOrg", "TargetRepo",
            "Status", "StartTime", "EndTime", "TimeTakenSeconds", "TimeTakenMinutes"
        ])

# Check repos.csv
if not os.path.exists(CSV_FILE):
    log_message(f"CSV file {CSV_FILE} not found. Please create with columns: CURRENT-NAME,NEW-NAME", "ERROR")
    exit(1)

# Read and process each repo
with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        current_name = row.get("CURRENT-NAME", "").strip()
        new_name = row.get("NEW-NAME", "").strip()
        if not current_name or not new_name:
            log_message("Missing CURRENT-NAME or NEW-NAME in CSV row. Skipping.", "ERROR")
            continue

        log_message(f"Migrating '{current_name}' -> '{new_name}'...")
        start_time = datetime.now()
        status = "Success"

        command = [
            "gh", "gei", "migrate-repo",
            "--github-source-org", SOURCE,
            "--source-repo", current_name,
            "--github-target-org", DESTINATION,
            "--target-repo", new_name
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            output = result.stdout + result.stderr
            log_message(f"Command output for '{current_name}': {output}")
            if result.returncode != 0 or "error" in output.lower() or "failed" in output.lower():
                status = "Failed"
                repo_log_file = os.path.join(LOGS_DIR, f"{current_name}.log")
                with open(repo_log_file, "w", encoding="utf-8") as logf:
                    logf.write(output)
                log_message(f"Error log saved to {repo_log_file}", "ERROR")
        except Exception as e:
            status = "Failed"
            repo_log_file = os.path.join(LOGS_DIR, f"{current_name}.log")
            with open(repo_log_file, "w", encoding="utf-8") as logf:
                logf.write(str(e))
            log_message(f"Exception caught during migration of '{current_name}'. See {repo_log_file} for details.", "ERROR")

        end_time = datetime.now()
        time_taken = round((end_time - start_time).total_seconds(), 2)
        time_taken_minutes = round(time_taken / 60, 2)

        # Write details to CSV
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                SOURCE, current_name, DESTINATION, new_name,
                status, start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"), time_taken, time_taken_minutes
            ])
        log_message(f"Migration result: Status={status}, Duration={time_taken}s ({time_taken_minutes}m)")

log_message("All repository migrations complete!")