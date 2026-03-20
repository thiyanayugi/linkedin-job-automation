"""
Telegram Notifier Module

Delivers real-time job match notifications and run summaries to the user's
Telegram account using the python-telegram-bot library. HTML formatting is
enabled for richer message presentation.
"""

import os
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from utils import setup_logger, retry_on_failure

logger = setup_logger(__name__)


class TelegramNotifier:
    """
    Deliver job match alerts and run summaries via a Telegram bot.
    
    Supports sending raw text messages, structured job notifications with
    score and apply-link, batch run summaries, and error alerts. All methods
    silently no-op when notifications are disabled (enabled=False).
    """
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Create and validate the Telegram bot connection.
        
        If credentials are missing or the Bot instantiation raises an exception,
        the notifier self-disables (enabled = False) rather than crashing the
        entire automation pipeline.
        
        Args:
            bot_token: Token issued by @BotFather for the Telegram bot.
            chat_id: Numeric or string ID of the Telegram chat to send messages to.
            enabled: Set to False to suppress all notifications (default: True).
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        # bot is lazily assigned only when credentials are valid
        self.bot = None
        
        if self.enabled:
            # Guard: both token and chat_id must be provided for the bot to work
            if not bot_token or not chat_id:
                logger.warning("Telegram credentials missing, notifications disabled")
                # Self-disable to prevent repeated failed send attempts later
                self.enabled = False
            else:
                try:
                    self.bot = Bot(token=bot_token)
                    logger.info("Initialized TelegramNotifier")
                except Exception as e:
                    logger.error(f"Failed to initialize Telegram bot: {str(e)}")
                    # Gracefully degrade: disable rather than raising to avoid
                    # crashing the entire automation pipeline on a notification failure
                    self.enabled = False
        else:
            logger.info("Telegram notifications disabled")
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def send_message(self, message: str) -> bool:
        """
        Send a text message via Telegram with HTML formatting support.
        
        Messages are sent with HTML parse mode enabled, allowing for
        rich formatting like <b>bold</b>, <i>italic</i>, and <a>links</a>.
        
        Args:
            message: Message text to send (supports HTML formatting)
        
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
        Format and send a rich job match notification via Telegram.
        
        Delegates formatting to _format_job_message() and sends the result
        through the Telegram bot. Returns False immediately if notifications
        are disabled.
        
        Args:
            job_data: Dictionary with keys 'title', 'company', 'location',
                      'score', and 'apply_link'.
        
        Returns:
            True if the message was delivered, False otherwise.
        """
        if not self.enabled:
            return False
        
        # Format the message
        message = self._format_job_message(job_data)
        
        return self.send_message(message)
    
    def _format_job_message(self, job_data: dict) -> str:
        """
        Build an HTML-formatted Telegram message for a single job match.
        
        Pulls title, company, location, score, and apply_link from job_data,
        supplying sensible defaults when fields are missing. The returned
        string uses HTML tags supported by Telegram's parse_mode='HTML'.
        
        Args:
            job_data: Dictionary containing job fields
        
        Returns:
            HTML-formatted notification string
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
        Send a formatted summary of the completed job search batch.
        
        Builds a summary message displaying the three key metrics and delivers
        it via Telegram. Useful for a quick end-of-run status report.
        
        Args:
            total_jobs: Total number of LinkedIn job listings found.
            matched_jobs: Number of jobs that were successfully AI-scored.
            high_score_jobs: Number of jobs that exceeded the score threshold.
        
        Returns:
            True if the summary was delivered, False otherwise.
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
        Deliver an error alert to the configured Telegram chat.
        
        Wraps the raw error string in a descriptive HTML-formatted message
        so the user is informed of failures without having to inspect logs.
        
        Args:
            error_message: Human-readable description of the error that occurred.
        
        Returns:
            True if the alert was delivered successfully, False otherwise.
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
