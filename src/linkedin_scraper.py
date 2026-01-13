"""
LinkedIn Scraper Module

Fetches and parses LinkedIn job listings using HTTP requests and BeautifulSoup.
Implements rate limiting and retry logic to handle network issues gracefully.
"""

import re
import time
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from utils import setup_logger, retry_on_failure, rate_limit, clean_html_text

logger = setup_logger(__name__)


class LinkedInScraper:
    """Scrape LinkedIn job listings based on search criteria."""
    
    def __init__(self, delay_seconds: int = 10):
        """
        Initialize the LinkedIn scraper.
        
        Args:
            delay_seconds: Delay between requests to avoid rate limiting
        """
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info(f"Initialized LinkedInScraper with {delay_seconds}s delay")
    
    def build_search_url(self, filters: Dict[str, any]) -> str:
        """
        Build LinkedIn search URL from filters.
        
        Constructs a LinkedIn job search URL by encoding filter parameters
        into query string format. Uses LinkedIn's specific parameter codes
        for experience levels, remote work types, and job types.
        
        Args:
            filters: Dictionary containing search filters (keyword, location, etc.)
        
        Returns:
            LinkedIn search URL with encoded filter parameters
        """
        # Base URL with jobs from last 24 hours (f_TPR=r86400)
        # r86400 = recent 86400 seconds (24 hours)
        url = "https://www.linkedin.com/jobs/search/?f_TPR=r86400"
        
        # Add keyword search term
        if filters.get("keyword"):
            url += f"&keywords={filters['keyword']}"
        
        # Add geographic location filter
        if filters.get("location"):
            url += f"&location={filters['location']}"
        
        # Add experience level filter (f_E parameter)
        # LinkedIn uses numeric codes: 1=Internship, 2=Entry, 3=Associate, etc.
        if filters.get("experience_level"):
            experience_map = {
                "Internship": "1",
                "Entry level": "2",
                "Associate": "3",
                "Mid-Senior level": "4",
                "Director": "5",
                "Executive": "6"
            }
            
            levels = [level.strip() for level in filters["experience_level"].split(",")]
            level_codes = [experience_map.get(level) for level in levels if level in experience_map]
            
            if level_codes:
                url += f"&f_E={','.join(level_codes)}"
        
        # Add remote/work type filter (f_WT parameter)
        # 1=On-Site, 2=Remote, 3=Hybrid
        if filters.get("remote"):
            remote_map = {
                "On-Site": "1",
                "Remote": "2",
                "Hybrid": "3"
            }
            
            remote_types = [rt.strip() for rt in filters["remote"].split(",")]
            remote_codes = [remote_map.get(rt) for rt in remote_types if rt in remote_map]
            
            if remote_codes:
                url += f"&f_WT={','.join(remote_codes)}"
        
        # Add job type filter (f_JT parameter)
        # F=Full-time, P=Part-time, C=Contract, T=Temporary, etc.
        if filters.get("job_type"):
            job_type_map = {
                "Full-time": "F",
                "Part-time": "P",
                "Contract": "C",
                "Temporary": "T",
                "Other": "O",
                "Internship": "I"
            }
            
            job_types = [jt.strip() for jt in filters["job_type"].split(",")]
            job_codes = [job_type_map.get(jt) for jt in job_types if jt in job_type_map]
            
            if job_codes:
                url += f"&f_JT={','.join(job_codes)}"
        
        # Add easy apply filter (f_EA=true)
        # Filters jobs that have LinkedIn's "Easy Apply" feature
        if filters.get("easy_apply"):
            url += "&f_EA=true"
        
        logger.info(f"Built search URL: {url}")
        return url
    
    @retry_on_failure(max_retries=3, delay=2.0)
    @rate_limit(calls=1, period=2.0)
    def fetch_search_results(self, search_url: str) -> str:
        """
        Fetch the search results page HTML.
        
        Args:
            search_url: LinkedIn search URL
        
        Returns:
            HTML content of the search results page
        """
        logger.info(f"Fetching search results from LinkedIn")
        
        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully fetched search results (status: {response.status_code})")
            return response.text
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch search results: {str(e)}")
            raise
    
    def extract_job_links(self, html: str) -> List[str]:
        """
        Extract job links from search results HTML.
        
        Args:
            html: HTML content of search results page
        
        Returns:
            List of job URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all job card links
        job_links = []
        
        # LinkedIn job cards typically have this structure
        job_cards = soup.select('ul.jobs-search__results-list li div a[class*="base-card"]')
        
        for card in job_cards:
            href = card.get('href')
            if href:
                # Clean up the URL
                if '?' in href:
                    href = href.split('?')[0]
                job_links.append(href)
        
        logger.info(f"Extracted {len(job_links)} job links from search results")
        return job_links
    
    @retry_on_failure(max_retries=3, delay=2.0)
    @rate_limit(calls=1, period=2.0)
    def fetch_job_details(self, job_url: str) -> Optional[Dict[str, str]]:
        """
        Fetch detailed information for a specific job.
        
        Args:
            job_url: URL of the job posting
        
        Returns:
            Dictionary containing job details
        """
        logger.info(f"Fetching job details from: {job_url}")
        
        try:
            # Add delay to avoid rate limiting
            time.sleep(self.delay_seconds)
            
            response = self.session.get(job_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract job details
            job_data = {
                'url': job_url,
                'title': '',
                'company': '',
                'location': '',
                'description': '',
                'job_id': ''
            }
            
            # Extract title
            title_elem = soup.select_one('div h1')
            if title_elem:
                job_data['title'] = clean_html_text(title_elem.get_text())
            
            # Extract company
            company_elem = soup.select_one('div span a')
            if company_elem:
                job_data['company'] = clean_html_text(company_elem.get_text())
            
            # Extract location
            location_elem = soup.select_one("div span[class*='topcard__flavor topcard__flavor--bullet']")
            if location_elem:
                job_data['location'] = clean_html_text(location_elem.get_text())
            
            # Extract description
            desc_elem = soup.select_one('div.description__text.description__text--rich')
            if desc_elem:
                job_data['description'] = clean_html_text(desc_elem.get_text())
            
            # Extract job ID
            job_id_elem = soup.select_one("a[data-item-type='semaphore']")
            if job_id_elem:
                job_id = job_id_elem.get('data-semaphore-content-urn', '')
                if job_id:
                    job_data['job_id'] = job_id.split(':')[-1]
            
            # If job_id not found, try to extract from URL
            if not job_data['job_id']:
                match = re.search(r'/jobs/view/(\d+)', job_url)
                if match:
                    job_data['job_id'] = match.group(1)
            
            # Generate apply link
            if job_data['job_id']:
                job_data['apply_link'] = f"https://www.linkedin.com/jobs/view/{job_data['job_id']}"
            else:
                job_data['apply_link'] = job_url
            
            logger.info(f"Successfully extracted job: {job_data['title']} at {job_data['company']}")
            return job_data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch job details: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing job details: {str(e)}")
            return None
    
    def search_jobs(self, filters: Dict[str, any], max_jobs: int = 25) -> List[Dict[str, str]]:
        """
        Search for jobs based on filters and return detailed information.
        
        Args:
            filters: Dictionary containing search filters
            max_jobs: Maximum number of jobs to fetch details for
        
        Returns:
            List of job dictionaries
        """
        logger.info(f"Starting job search with filters: {filters}")
        
        # Build search URL
        search_url = self.build_search_url(filters)
        
        # Fetch search results
        html = self.fetch_search_results(search_url)
        
        # Extract job links
        job_links = self.extract_job_links(html)
        
        if not job_links:
            logger.warning("No job links found in search results")
            return []
        
        # Limit number of jobs
        job_links = job_links[:max_jobs]
        logger.info(f"Processing {len(job_links)} jobs")
        
        # Fetch details for each job
        jobs = []
        for i, job_url in enumerate(job_links, 1):
            logger.info(f"Processing job {i}/{len(job_links)}")
            
            job_data = self.fetch_job_details(job_url)
            if job_data:
                jobs.append(job_data)
        
        logger.info(f"Successfully fetched details for {len(jobs)} jobs")
        return jobs


def main():
    """Test the LinkedIn scraper."""
    import json
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Load filters
    filters_path = "config/filters.json"
    if not os.path.exists(filters_path):
        print(f"❌ Filters file not found: {filters_path}")
        return
    
    with open(filters_path, 'r') as f:
        filters = json.load(f)
    
    print("\n" + "="*80)
    print("LINKEDIN SCRAPER TEST")
    print("="*80)
    print(f"\n🔍 Search Filters:")
    for key, value in filters.items():
        print(f"  {key}: {value}")
    
    scraper = LinkedInScraper(delay_seconds=2)
    
    # Test with just 3 jobs
    jobs = scraper.search_jobs(filters, max_jobs=3)
    
    print(f"\n📊 Found {len(jobs)} jobs:\n")
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   URL: {job['apply_link']}")
        print()
    
    print("="*80)
    print("✅ LinkedIn scraping test complete!")


if __name__ == "__main__":
    main()
