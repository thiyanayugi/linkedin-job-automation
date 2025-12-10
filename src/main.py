"""
Main Application
Orchestrates the LinkedIn job search automation.
"""

import os
import sys
import json
import argparse
import time
import schedule
from datetime import datetime
from dotenv import load_dotenv

from resume_parser import ResumeParser
from linkedin_scraper import LinkedInScraper
from ai_matcher import AIMatcher
from sheets_manager import SheetsManager
from notifier import TelegramNotifier
from utils import setup_logger, parse_time_string

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger(
    __name__,
    log_file=os.getenv("LOG_FILE", "logs/app.log"),
    level=os.getenv("LOG_LEVEL", "INFO")
)


class JobSearchAutomation:
    """Main automation orchestrator."""
    
    def __init__(self):
        """Initialize the automation with all components."""
        logger.info("="*80)
        logger.info("Initializing LinkedIn Job Search Automation")
        logger.info("="*80)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.resume_parser = None
        self.scraper = None
        self.ai_matcher = None
        self.sheets_manager = None
        self.notifier = None
        
        self._initialize_components()
        
        logger.info("Initialization complete")
    
    def _load_config(self) -> dict:
        """Load configuration from environment and files."""
        config = {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'google_credentials': os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
            'google_sheet_id': os.getenv('GOOGLE_SHEET_ID'),
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'telegram_enabled': os.getenv('ENABLE_TELEGRAM', 'false').lower() == 'true',
            'min_score': int(os.getenv('MIN_SCORE_THRESHOLD', '50')),
            'max_jobs': int(os.getenv('MAX_JOBS_PER_RUN', '25')),
            'request_delay': int(os.getenv('REQUEST_DELAY_SECONDS', '10')),
            'resume_path': os.getenv('RESUME_PATH', 'data/resume.pdf'),
            'filters_path': 'config/filters.json'
        }
        
        # Validate required config
        required = ['openai_api_key', 'google_credentials', 'google_sheet_id', 'resume_path']
        missing = [key for key in required if not config.get(key)]
        
        if missing:
            logger.error(f"Missing required configuration: {', '.join(missing)}")
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return config
    
    def _initialize_components(self):
        """Initialize all automation components."""
        try:
            # Resume Parser
            logger.info("Initializing Resume Parser...")
            self.resume_parser = ResumeParser(self.config['resume_path'])
            
            # LinkedIn Scraper
            logger.info("Initializing LinkedIn Scraper...")
            self.scraper = LinkedInScraper(delay_seconds=self.config['request_delay'])
            
            # AI Matcher
            logger.info("Initializing AI Matcher...")
            self.ai_matcher = AIMatcher(
                api_key=self.config['openai_api_key'],
                model=self.config['openai_model']
            )
            
            # Google Sheets Manager
            logger.info("Initializing Google Sheets Manager...")
            self.sheets_manager = SheetsManager(
                credentials_file=self.config['google_credentials'],
                sheet_id=self.config['google_sheet_id']
            )
            
            # Telegram Notifier
            logger.info("Initializing Telegram Notifier...")
            self.notifier = TelegramNotifier(
                bot_token=self.config['telegram_token'],
                chat_id=self.config['telegram_chat_id'],
                enabled=self.config['telegram_enabled']
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            raise
    
    def _load_filters(self) -> dict:
        """Load job search filters from file."""
        filters_path = self.config['filters_path']
        
        if not os.path.exists(filters_path):
            logger.error(f"Filters file not found: {filters_path}")
            raise FileNotFoundError(f"Filters file not found: {filters_path}")
        
        with open(filters_path, 'r') as f:
            filters = json.load(f)
        
        logger.info(f"Loaded search filters: {filters}")
        return filters
    
    def run(self):
        """Execute the job search automation."""
        start_time = datetime.now()
        logger.info("="*80)
        logger.info(f"Starting job search automation at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        try:
            # Step 1: Extract resume text
            logger.info("\n[1/6] Extracting resume text...")
            resume_text = self.resume_parser.extract_text()
            logger.info(f"Resume extracted: {len(resume_text)} characters")
            
            # Step 2: Load search filters
            logger.info("\n[2/6] Loading search filters...")
            filters = self._load_filters()
            
            # Step 3: Search for jobs on LinkedIn
            logger.info("\n[3/6] Searching LinkedIn for jobs...")
            jobs = self.scraper.search_jobs(filters, max_jobs=self.config['max_jobs'])
            logger.info(f"Found {len(jobs)} jobs")
            
            if not jobs:
                logger.warning("No jobs found, exiting")
                self.notifier.send_message("⚠️ No jobs found in this search")
                return
            
            # Step 4: Match jobs with AI
            logger.info("\n[4/6] Matching jobs with AI...")
            matched_jobs = self.ai_matcher.batch_match_jobs(resume_text, jobs)
            logger.info(f"Matched {len(matched_jobs)} jobs")
            
            # Step 5: Filter jobs by score
            logger.info(f"\n[5/6] Filtering jobs (min score: {self.config['min_score']})...")
            high_score_jobs = [job for job in matched_jobs if job.get('score', 0) >= self.config['min_score']]
            logger.info(f"Found {len(high_score_jobs)} jobs above threshold")
            
            # Step 6: Save to Google Sheets and send notifications
            logger.info("\n[6/6] Saving results and sending notifications...")
            
            # Ensure sheet has headers
            self.sheets_manager.ensure_headers()
            
            # Save all matched jobs to sheet
            self.sheets_manager.batch_append_jobs(matched_jobs)
            
            # Send individual notifications for high-scoring jobs
            for job in high_score_jobs:
                logger.info(f"Sending notification for: {job.get('title', 'Unknown')}")
                self.notifier.send_job_notification(job)
                time.sleep(1)  # Small delay between notifications
            
            # Send summary
            self.notifier.send_batch_summary(
                total_jobs=len(jobs),
                matched_jobs=len(matched_jobs),
                high_score_jobs=len(high_score_jobs)
            )
            
            # Completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("="*80)
            logger.info(f"Job search automation completed successfully!")
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info(f"Jobs found: {len(jobs)}")
            logger.info(f"Jobs matched: {len(matched_jobs)}")
            logger.info(f"High-scoring jobs: {len(high_score_jobs)}")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"Automation failed: {str(e)}", exc_info=True)
            self.notifier.send_error_notification(str(e))
            raise


def run_once():
    """Run the automation once."""
    automation = JobSearchAutomation()
    automation.run()


def run_scheduled():
    """Run the automation on a schedule."""
    schedule_time = os.getenv('SCHEDULE_TIME', '17:00')
    
    try:
        hour, minute = parse_time_string(schedule_time)
        schedule_str = f"{hour:02d}:{minute:02d}"
    except ValueError as e:
        logger.error(f"Invalid schedule time: {str(e)}")
        sys.exit(1)
    
    logger.info(f"Scheduling job search to run daily at {schedule_str}")
    
    # Schedule the job
    schedule.every().day.at(schedule_str).do(run_once)
    
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='LinkedIn Job Search Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run once:           python src/main.py
  Run on schedule:    python src/main.py --schedule
  
For more information, see README.md
        """
    )
    
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run on schedule (time configured in .env)'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "="*80)
    print("LinkedIn Job Search Automation".center(80))
    print("="*80 + "\n")
    
    try:
        if args.schedule:
            run_scheduled()
        else:
            run_once()
    
    except KeyboardInterrupt:
        logger.info("\nStopped by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
