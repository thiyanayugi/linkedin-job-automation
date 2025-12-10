"""
Telegram Notifier Module
Sends notifications via Telegram bot.
"""

import os
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from utils import setup_logger, retry_on_failure

logger = setup_logger(__name__)


class TelegramNotifier:
    """Send job notifications via Telegram."""
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Initialize the Telegram notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
            enabled: Whether notifications are enabled
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.bot = None
        
        if self.enabled:
            if not bot_token or not chat_id:
                logger.warning("Telegram credentials missing, notifications disabled")
                self.enabled = False
            else:
                try:
                    self.bot = Bot(token=bot_token)
                    logger.info("Initialized TelegramNotifier")
                except Exception as e:
                    logger.error(f"Failed to initialize Telegram bot: {str(e)}")
                    self.enabled = False
        else:
            logger.info("Telegram notifications disabled")
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def send_message(self, message: str) -> bool:
        """
        Send a text message via Telegram.
        
        Args:
            message: Message text to send
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping message")
            return False
        
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            
            logger.info("Successfully sent Telegram message")
            return True
        
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {str(e)}")
            return False
    
    def send_job_notification(self, job_data: dict) -> bool:
        """
        Send a formatted job notification.
        
        Args:
            job_data: Dictionary containing job information
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        # Format the message
        message = self._format_job_message(job_data)
        
        return self.send_message(message)
    
    def _format_job_message(self, job_data: dict) -> str:
        """
        Format a job notification message.
        
        Args:
            job_data: Dictionary containing job information
        
        Returns:
            Formatted message string
        """
        title = job_data.get('title', 'Unknown Position')
        company = job_data.get('company', 'Unknown Company')
        location = job_data.get('location', 'Unknown Location')
        score = job_data.get('score', 0)
        apply_link = job_data.get('apply_link', '')
        
        message = f"""🎯 <b>New Job Match!</b>

<b>Title:</b> {title}
<b>Company:</b> {company}
<b>Location:</b> {location}
<b>Match Score:</b> {score}/100

<b>Apply:</b> {apply_link}"""
        
        return message
    
    def send_batch_summary(self, total_jobs: int, matched_jobs: int, high_score_jobs: int) -> bool:
        """
        Send a summary of the job search batch.
        
        Args:
            total_jobs: Total number of jobs found
            matched_jobs: Number of jobs matched
            high_score_jobs: Number of high-scoring jobs
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        message = f"""📊 <b>Job Search Summary</b>

🔍 Jobs Found: {total_jobs}
✅ Jobs Matched: {matched_jobs}
⭐ High Scores: {high_score_jobs}

Check your Google Sheet for details!"""
        
        return self.send_message(message)
    
    def send_error_notification(self, error_message: str) -> bool:
        """
        Send an error notification.
        
        Args:
            error_message: Error message to send
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        message = f"""⚠️ <b>Job Search Error</b>

An error occurred during the job search:

{error_message}

Please check the logs for more details."""
        
        return self.send_message(message)


def main():
    """Test the Telegram notifier."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    enabled = os.getenv("ENABLE_TELEGRAM", "false").lower() == "true"
    
    if not enabled:
        print("⚠️  Telegram notifications are disabled in .env")
        print("Set ENABLE_TELEGRAM=true to enable")
        sys.exit(0)
    
    if not bot_token or not chat_id:
        print("❌ Missing Telegram configuration in .env file")
        print("Required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        print("\nTo set up Telegram notifications:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the bot token to your .env file")
        print("4. Start a chat with your bot")
        print("5. Get your chat ID from: https://api.telegram.org/bot<TOKEN>/getUpdates")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("TELEGRAM NOTIFIER TEST")
    print("="*80)
    
    notifier = TelegramNotifier(bot_token, chat_id, enabled=True)
    
    # Test simple message
    print("\n📱 Sending test message...")
    success = notifier.send_message("🧪 <b>Test Message</b>\n\nThis is a test from your LinkedIn Job Automation!")
    
    if success:
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message")
        sys.exit(1)
    
    # Test job notification
    print("\n📱 Sending test job notification...")
    sample_job = {
        'title': 'Senior Software Engineer',
        'company': 'Tech Company Inc.',
        'location': 'Berlin, Germany',
        'score': 85,
        'apply_link': 'https://example.com/job/12345'
    }
    
    success = notifier.send_job_notification(sample_job)
    
    if success:
        print("✅ Job notification sent successfully!")
    else:
        print("❌ Failed to send job notification")
        sys.exit(1)
    
    # Test summary
    print("\n📱 Sending test summary...")
    success = notifier.send_batch_summary(total_jobs=10, matched_jobs=7, high_score_jobs=3)
    
    if success:
        print("✅ Summary sent successfully!")
    else:
        print("❌ Failed to send summary")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ Telegram notifier test complete!")
    print("\nCheck your Telegram to see the test messages.")


if __name__ == "__main__":
    main()
