"""
Google Sheets Manager Module
Handles reading from and writing to Google Sheets.
"""

import os
from typing import List, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials
from utils import setup_logger, retry_on_failure

logger = setup_logger(__name__)


class SheetsManager:
    """Manage Google Sheets operations for job data."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, credentials_file: str, sheet_id: str):
        """
        Initialize the Google Sheets manager.
        
        Args:
            credentials_file: Path to Google service account credentials JSON
            sheet_id: Google Sheet ID
        """
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.client = None
        self.spreadsheet = None
        
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
        
        self._authenticate()
        
        logger.info(f"Initialized SheetsManager for sheet: {sheet_id}")
    
    def _authenticate(self):
        """
        Authenticate with Google Sheets API using service account credentials.
        
        Establishes connection to Google Sheets API using OAuth2 credentials
        from the service account JSON file. Requires both Sheets and Drive scopes
        for full read/write access.
        
        Raises:
            FileNotFoundError: If credentials file doesn't exist
            Exception: If authentication fails or sheet cannot be accessed
        """
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            
            logger.info("Successfully authenticated with Google Sheets API")
        
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def read_filters(self, worksheet_name: str = "Filter") -> Optional[Dict[str, any]]:
        """
        Read job search filters from Google Sheet.
        
        Args:
            worksheet_name: Name of the worksheet containing filters
        
        Returns:
            Dictionary of filters
        """
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            
            # Get all values
            rows = worksheet.get_all_values()
            
            if len(rows) < 2:
                logger.warning("Filter sheet has insufficient data")
                return None
            
            # First row is headers, second row is values
            headers = rows[0]
            values = rows[1]
            
            filters = {}
            for i, header in enumerate(headers):
                if i < len(values):
                    filters[header] = values[i]
            
            logger.info(f"Read filters from sheet: {filters}")
            return filters
        
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{worksheet_name}' not found")
            return None
        except Exception as e:
            logger.error(f"Failed to read filters: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def append_job(self, job_data: Dict[str, any], worksheet_name: str = "Sheet1"):
        """
        Append a job to the Google Sheet.
        
        Args:
            job_data: Dictionary containing job information
            worksheet_name: Name of the worksheet to append to
        """
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            
            # Prepare row data
            row = [
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('location', ''),
                job_data.get('apply_link', ''),
                job_data.get('score', 0),
                job_data.get('description', ''),
                job_data.get('coverLetter', '')
            ]
            
            # Append the row
            worksheet.append_row(row, value_input_option='USER_ENTERED')
            
            logger.info(f"Appended job to sheet: {job_data.get('title', 'Unknown')}")
        
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{worksheet_name}' not found")
            raise
        except Exception as e:
            logger.error(f"Failed to append job: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def update_or_append_job(self, job_data: Dict[str, any], worksheet_name: str = "Sheet1"):
        """
        Update existing job or append new one based on job link.
        
        Args:
            job_data: Dictionary containing job information
            worksheet_name: Name of the worksheet
        """
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            
            # Get all values
            all_values = worksheet.get_all_values()
            
            if not all_values:
                # Sheet is empty, add headers
                headers = ['Title', 'Company', 'Location', 'Link', 'Score', 'Description', 'Cover Letter']
                worksheet.append_row(headers, value_input_option='USER_ENTERED')
                all_values = [headers]
            
            # Find if job already exists (match by link)
            job_link = job_data.get('apply_link', '')
            existing_row_index = None
            
            for i, row in enumerate(all_values[1:], start=2):  # Skip header row
                if len(row) > 3 and row[3] == job_link:
                    existing_row_index = i
                    break
            
            # Prepare row data
            row = [
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('location', ''),
                job_data.get('apply_link', ''),
                job_data.get('score', 0),
                job_data.get('description', ''),
                job_data.get('coverLetter', '')
            ]
            
            if existing_row_index:
                # Update existing row
                for col_index, value in enumerate(row, start=1):
                    worksheet.update_cell(existing_row_index, col_index, value)
                logger.info(f"Updated existing job in sheet: {job_data.get('title', 'Unknown')}")
            else:
                # Append new row
                worksheet.append_row(row, value_input_option='USER_ENTERED')
                logger.info(f"Appended new job to sheet: {job_data.get('title', 'Unknown')}")
        
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{worksheet_name}' not found")
            raise
        except Exception as e:
            logger.error(f"Failed to update/append job: {str(e)}")
            raise
    
    def batch_append_jobs(self, jobs: List[Dict[str, any]], worksheet_name: str = "Sheet1"):
        """
        Append multiple jobs to the Google Sheet.
        
        Args:
            jobs: List of job dictionaries
            worksheet_name: Name of the worksheet
        """
        logger.info(f"Batch appending {len(jobs)} jobs to sheet")
        
        for i, job in enumerate(jobs, 1):
            try:
                logger.info(f"Appending job {i}/{len(jobs)}")
                self.update_or_append_job(job, worksheet_name)
            except Exception as e:
                logger.error(f"Failed to append job {i}: {str(e)}")
                # Continue with next job
                continue
        
        logger.info(f"Batch append complete")
    
    def ensure_headers(self, worksheet_name: str = "Sheet1"):
        """
        Ensure the worksheet has proper headers for job data storage.
        
        Validates that the worksheet has the correct header row with all
        required columns. If headers are missing or incorrect, they will
        be added or inserted at the top of the sheet.
        
        Expected headers: Title, Company, Location, Link, Score, Description, Cover Letter
        
        Args:
            worksheet_name: Name of the worksheet to validate
            
        Raises:
            Exception: If worksheet access or header insertion fails
        """
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            
            # Check if sheet is empty or has no headers
            all_values = worksheet.get_all_values()
            
            # Define expected header structure
            if not all_values or all_values[0] != ['Title', 'Company', 'Location', 'Link', 'Score', 'Description', 'Cover Letter']:
                headers = ['Title', 'Company', 'Location', 'Link', 'Score', 'Description', 'Cover Letter']
                
                if not all_values:
                    # Sheet is empty, append headers
                    worksheet.append_row(headers, value_input_option='USER_ENTERED')
                else:
                    # Sheet has data but wrong headers, insert at top
                    worksheet.insert_row(headers, index=1, value_input_option='USER_ENTERED')
                
                logger.info(f"Added headers to worksheet: {worksheet_name}")
        
        except Exception as e:
            logger.error(f"Failed to ensure headers: {str(e)}")
            raise


def main():
    """Test the Google Sheets manager."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    if not credentials_file or not sheet_id:
        print("❌ Missing Google Sheets configuration in .env file")
        print("Required: GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEET_ID")
        sys.exit(1)
    
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("\nPlease follow these steps:")
        print("1. Go to Google Cloud Console")
        print("2. Create a service account")
        print("3. Download the JSON credentials")
        print("4. Save it to config/google_credentials.json")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("GOOGLE SHEETS MANAGER TEST")
    print("="*80)
    
    try:
        manager = SheetsManager(credentials_file, sheet_id)
        
        # Test ensuring headers
        print("\n📋 Ensuring headers...")
        manager.ensure_headers()
        
        # Test appending a sample job
        sample_job = {
            'title': 'Test Software Engineer',
            'company': 'Test Company',
            'location': 'Test Location',
            'apply_link': 'https://example.com/job/12345',
            'score': 85,
            'description': 'This is a test job description',
            'coverLetter': 'This is a test cover letter'
        }
        
        print("\n📝 Appending test job...")
        manager.update_or_append_job(sample_job)
        
        print("\n" + "="*80)
        print("✅ Google Sheets test complete!")
        print("\nCheck your Google Sheet to see the test job entry.")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
