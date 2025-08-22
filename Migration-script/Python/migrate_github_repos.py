import os
import csv
import subprocess
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

def setup_logging(log_file: str) -> None:
    """Initialize logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def create_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(exist_ok=True)

def validate_env_vars() -> bool:
    """Validate required environment variables."""
    required_vars = ['GH_SOURCE_PAT', 'GH_PAT', 'SOURCE', 'DESTINATION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"Required environment variables missing: {', '.join(missing_vars)}")
        return False
    return True

def initialize_csv_output(output_file: str) -> None:
    """Initialize the output CSV file with headers."""
    if not Path(output_file).exists():
        headers = ['SourceOrg', 'SourceRepo', 'TargetOrg', 'TargetRepo', 
                  'Status', 'StartTime', 'EndTime', 'TimeTakenSeconds', 'TimeTakenMinutes']
        with open(output_file, 'w', newline='') as f:
            csv.writer(f).writerow(headers)

def migrate_repository(current_name: str, new_name: str, logs_folder: str, output_csv: str) -> None:
    """Migrate a single repository and log the results."""
    start_time = datetime.now()
    status = "Success"
    
    command = f"gh gei migrate-repo --github-source-org {os.getenv('SOURCE')} " \
              f"--source-repo {current_name} --github-target-org {os.getenv('DESTINATION')} " \
              f"--target-repo {new_name}"
    
    try:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if output.returncode != 0 or 'error' in output.stdout.lower() or 'failed' in output.stdout.lower():
            status = "Failed"
            repo_log_file = Path(logs_folder) / f"{current_name}.log"
            with open(repo_log_file, 'w') as f:
                f.write(output.stdout + output.stderr)
            logging.error(f"Error log saved to {repo_log_file}")
        
        logging.info(f"Command output for '{current_name}': {output.stdout}")
        
    except Exception as e:
        status = "Failed"
        repo_log_file = Path(logs_folder) / f"{current_name}.log"
        with open(repo_log_file, 'w') as f:
            f.write(str(e))
        logging.error(f"Exception caught during migration of '{current_name}'. See {repo_log_file} for details.")
    
    end_time = datetime.now()
    time_taken = (end_time - start_time).total_seconds()
      # Write migration details to CSV
    with open(output_csv, 'a', newline='') as f:
        csv.writer(f).writerow([
            os.getenv('SOURCE'),
            current_name,
            os.getenv('DESTINATION'),
            new_name,
            status,
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            f"{time_taken:.2f}",
            f"{(time_taken / 60):.2f}"
        ])
    
    logging.info(f"Migration result: Status={status}, Duration={time_taken:.2f}s")

def main():
    # Initialize constants
    LOG_FILE = "MigrationLog.txt"
    OUTPUT_CSV = "MigrationDetails.csv"
    LOGS_FOLDER = "logs"
    ENV_FILE = ".env"
    REPOS_CSV = "repos.csv"
    
    # Setup logging and create necessary directories
    setup_logging(LOG_FILE)
    create_directory(LOGS_FOLDER)
    
    logging.info("Starting GitHub repository migration script...")
    
    # Load environment variables
    if Path(ENV_FILE).exists():
        load_dotenv(ENV_FILE)
        logging.info(f"Loaded environment variables from {ENV_FILE}")
    else:
        logging.error(f"{ENV_FILE} file not found.")
        return
    
    # Validate environment variables
    if not validate_env_vars():
        return
    
    # Check for repos.csv
    if not Path(REPOS_CSV).exists():
        logging.error(f"CSV file {REPOS_CSV} not found. Please create with columns: CURRENT-NAME, NEW-NAME")
        return
    
    # Initialize output CSV
    initialize_csv_output(OUTPUT_CSV)
    
    # Process repositories
    with open(REPOS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            current_name = row.get('CURRENT-NAME')
            new_name = row.get('NEW-NAME')
            
            if not current_name or not new_name:
                logging.error("Missing CURRENT-NAME or NEW-NAME in CSV row. Skipping.")
                continue
            
            logging.info(f"Migrating '{current_name}' -> '{new_name}'...")
            migrate_repository(current_name, new_name, LOGS_FOLDER, OUTPUT_CSV)
    
    logging.info("All repository migrations complete!")

if __name__ == "__main__":
    main()
