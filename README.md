# LinkedIn Job Search Automation

A Python-based automation tool that searches LinkedIn for jobs, matches them against your resume using AI, generates custom cover letters, and notifies you of the best opportunities.

## Features

- 🔍 **Automated LinkedIn Job Search** - Searches LinkedIn based on customizable criteria including keywords, location, experience level, remote work preferences, and job type
- 🤖 **AI-Powered Matching** - Leverages OpenAI's GPT models to intelligently score job compatibility (0-100 scale) by analyzing your resume against job descriptions
- ✍️ **Auto Cover Letter Generation** - Creates personalized, tailored cover letters for each job opportunity using AI analysis
- 📊 **Google Sheets Integration** - Automatically saves all job details, compatibility scores, and generated cover letters to a centralized spreadsheet
- 📱 **Telegram Notifications** - Receive instant push notifications for high-scoring job matches directly to your Telegram account
- ⏰ **Scheduled Execution** - Configure the automation to run at your preferred time daily using built-in scheduling
- 🎯 **Smart Filtering** - Intelligently filters and saves only jobs that meet or exceed your minimum score threshold

## Prerequisites

- Python **3.8 or higher** (3.10+ recommended for best compatibility with dependencies)
- Google Cloud account with the **Sheets API** and **Drive API** enabled
- OpenAI API key with access to the `gpt-4o-mini` model (or a compatible chat model)
- Telegram Bot token from [@BotFather](https://t.me/botfather) *(optional — only needed for notifications)*
- A Google Sheets service account JSON credentials file

## Installation

1. Clone or navigate to this directory:

```bash
cd "/home/yugi/job application project"
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your configuration:

   - Copy `.env.example` to `.env`
   - Fill in your API keys and credentials
   - Update `config/filters.json` with your job search criteria

4. Add your resume:
   - Place your resume PDF in `data/resume.pdf`

## Configuration

### Environment Variables (.env)

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Google Sheets Credentials
GOOGLE_SHEETS_CREDENTIALS_FILE=config/google_credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Job Score Threshold
MIN_SCORE_THRESHOLD=50

# Schedule (24-hour format)
SCHEDULE_TIME=17:00
```

### Job Search Filters (config/filters.json)

```json
{
  "keyword": "Software Engineer",
  "location": "Berlin",
  "experience_level": "Mid-Senior level",
  "remote": "Remote,Hybrid",
  "job_type": "Full-time",
  "easy_apply": true
}
```

## Usage

### Run Once

```bash
python src/main.py
```

### Run on Schedule

```bash
python src/main.py --schedule
```

### Test Individual Components

```bash
# Test resume parsing
python src/resume_parser.py

# Test LinkedIn scraping
python src/linkedin_scraper.py

# Test AI matching
python src/ai_matcher.py
```

## Project Structure

```
linkedin-job-automation/
├── config/
│   ├── .env                    # Environment variables (create from .env.example)
│   ├── .env.example            # Example environment file
│   ├── filters.json            # Job search criteria
│   └── google_credentials.json # Google API credentials
├── src/
│   ├── main.py                 # Main orchestrator
│   ├── resume_parser.py        # PDF text extraction
│   ├── linkedin_scraper.py     # LinkedIn job scraping
│   ├── ai_matcher.py           # AI scoring & cover letter generation
│   ├── sheets_manager.py       # Google Sheets operations
│   ├── notifier.py             # Telegram notifications
│   └── utils.py                # Helper functions
├── data/
│   └── resume.pdf              # Your resume (add this)
├── logs/
│   └── app.log                 # Application logs
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Google Sheets Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Sheets API
4. Create credentials (Service Account)
5. Download the JSON credentials file
6. Save it as `config/google_credentials.json`
7. Share your Google Sheet with the service account email

### Expected Sheet Structure

**Sheet 1: Job Results**
| Title | Company | Location | Link | Score | Description | Cover Letter |
|-------|---------|----------|------|-------|-------------|--------------|

**Sheet 2: Filters**
| Keyword | Location | Experience Level | Remote | Job Type | Easy Apply |
|---------|----------|------------------|--------|----------|------------|

## Telegram Bot Setup (Optional)

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the bot token to your `.env` file
4. Start a chat with your bot
5. Get your chat ID by visiting: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
6. Add the chat ID to your `.env` file

## How It Works

1. **Initialization**: Loads your resume and search filters
2. **LinkedIn Search**: Constructs search URL and fetches job listings
3. **Job Extraction**: Parses HTML to extract job details
4. **AI Analysis**: For each job:
   - Compares job description with your resume
   - Generates compatibility score (0-100)
   - Creates personalized cover letter
5. **Filtering**: Only processes jobs above score threshold
6. **Storage**: Saves results to Google Sheets
7. **Notification**: Sends Telegram alert for high-scoring matches

## Troubleshooting

### LinkedIn Blocking Requests

- Add delays between requests (already implemented)
- Use a VPN if needed
- Consider using LinkedIn's official API (requires approval)

### Google Sheets Permission Error

- Ensure the service account email has edit access to your sheet
- Check that the credentials file path is correct

### OpenAI Rate Limits

- Reduce the number of jobs processed per run
- Increase delays between API calls
- Upgrade your OpenAI plan

## Legal & Ethical Considerations

⚠️ **Important**: Web scraping LinkedIn may violate their Terms of Service. This tool is for educational purposes. Consider:

- Using LinkedIn's official API
- Respecting rate limits
- Not sharing scraped data
- Using responsibly

## Contributing

Feel free to submit issues or pull requests to improve this project.

## License

MIT License - Use at your own risk

## Support

For questions or issues, please create an issue in the repository.

---

**Made with ❤️ to automate your job search**
