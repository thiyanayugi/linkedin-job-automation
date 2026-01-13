"""
AI Matcher Module
Uses OpenAI to match jobs with resume and generate cover letters.
"""

import os
import json
from typing import Dict, Optional
from openai import OpenAI
from utils import setup_logger, retry_on_failure

logger = setup_logger(__name__)


class AIMatcher:
    """Match jobs with resume using AI and generate cover letters."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize the AI matcher.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        logger.info(f"Initialized AIMatcher with model: {model}")
    
    def create_matching_prompt(self, resume_text: str, job_description: str) -> str:
        """
        Create the prompt for job matching and cover letter generation.
        
        Constructs a detailed prompt that instructs the AI to analyze the resume
        against the job description, calculate a matching score (0-100), and
        generate a tailored cover letter.
        
        Args:
            resume_text: Text content of the resume
            job_description: Job description text
        
        Returns:
            Formatted prompt string ready for OpenAI API
        """
        prompt = f"""Hi, you are a helpful job matcher. You read my resume then analyze the given resume and job description and provide a job matching score. Also write a cover letter based on my resume and the job description. 

Cover letter must be at least 2 paragraphs and ignore the name, address and signature part from start and end.

If you are using special characters like " use \\ to escape it. Output must be parseable JSON without error.

Your response should be ONLY a JSON object with this exact format:
{{"score": 80, "coverLetter": "sample cover letter"}}

Job Description:
{job_description}

My Resume:
{resume_text}

Remember: Return ONLY the JSON object, no other text."""
        
        return prompt
    
    @retry_on_failure(max_retries=3, delay=2.0, backoff=2.0)
    def match_job(self, resume_text: str, job_description: str) -> Optional[Dict[str, any]]:
        """
        Match a job with the resume and generate a cover letter.
        
        Args:
            resume_text: Text content of the resume
            job_description: Job description text
        
        Returns:
            Dictionary with 'score' and 'coverLetter' keys
        """
        if not job_description or len(job_description) < 50:
            logger.warning("Job description too short, skipping AI matching")
            return {"score": 0, "coverLetter": ""}
        
        logger.info("Sending job matching request to OpenAI")
        
        try:
            prompt = self.create_matching_prompt(resume_text, job_description)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional job matching assistant. You analyze resumes and job descriptions to provide matching scores and generate cover letters. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the response
            ai_output = response.choices[0].message.content.strip()
            
            logger.debug(f"AI Response: {ai_output}")
            
            # Parse JSON response
            # Remove markdown code blocks if present
            ai_output = ai_output.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(ai_output)
            
            # Validate response structure
            if 'score' not in result or 'coverLetter' not in result:
                logger.error("AI response missing required fields")
                return {"score": 0, "coverLetter": ""}
            
            # Ensure score is an integer between 0 and 100
            score = int(result['score'])
            score = max(0, min(100, score))
            
            logger.info(f"Job matching complete - Score: {score}")
            
            return {
                "score": score,
                "coverLetter": result['coverLetter']
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            logger.error(f"Raw response: {ai_output}")
            return {"score": 0, "coverLetter": ""}
        
        except Exception as e:
            logger.error(f"AI matching failed: {str(e)}")
            raise
    
    def batch_match_jobs(self, resume_text: str, jobs: list) -> list:
        """
        Match multiple jobs with the resume.
        
        Args:
            resume_text: Text content of the resume
            jobs: List of job dictionaries
        
        Returns:
            List of jobs with added 'score' and 'coverLetter' fields
        """
        logger.info(f"Starting batch matching for {len(jobs)} jobs")
        
        matched_jobs = []
        
        for i, job in enumerate(jobs, 1):
            logger.info(f"Matching job {i}/{len(jobs)}: {job.get('title', 'Unknown')}")
            
            try:
                result = self.match_job(resume_text, job.get('description', ''))
                
                if result:
                    job['score'] = result['score']
                    job['coverLetter'] = result['coverLetter']
                    matched_jobs.append(job)
                    
                    logger.info(f"Job matched with score: {result['score']}")
                else:
                    logger.warning(f"Skipping job due to matching failure")
            
            except Exception as e:
                logger.error(f"Error matching job {i}: {str(e)}")
                # Continue with next job
                continue
        
        logger.info(f"Batch matching complete: {len(matched_jobs)}/{len(jobs)} jobs matched")
        return matched_jobs


def main():
    """Test the AI matcher."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        sys.exit(1)
    
    # Sample data for testing
    sample_resume = """
    John Doe
    Senior Software Engineer
    
    Experience:
    - 5 years of Python development
    - Expert in web scraping and automation
    - Strong background in AI/ML integration
    - Experience with REST APIs and microservices
    
    Skills:
    Python, JavaScript, React, Node.js, Docker, AWS, OpenAI, TensorFlow
    """
    
    sample_job_description = """
    We are looking for a Senior Software Engineer with strong Python skills.
    
    Requirements:
    - 3+ years of Python experience
    - Experience with web automation
    - Knowledge of AI/ML technologies
    - Strong problem-solving skills
    
    Nice to have:
    - Docker experience
    - Cloud platform knowledge (AWS/GCP)
    """
    
    print("\n" + "="*80)
    print("AI MATCHER TEST")
    print("="*80)
    
    matcher = AIMatcher(api_key=api_key)
    
    print("\n🤖 Matching job with resume...\n")
    
    result = matcher.match_job(sample_resume, sample_job_description)
    
    if result:
        print(f"📊 Match Score: {result['score']}/100")
        print(f"\n📝 Cover Letter:\n")
        print(result['coverLetter'])
        print("\n" + "="*80)
        print("✅ AI matching test complete!")
    else:
        print("❌ AI matching failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
