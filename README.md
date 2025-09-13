# Amazon Careers Job Monitor

An automated system that monitors Amazon Careers for job count changes and sends email alerts when new positions are posted.

## Features

- **Automated Monitoring**: Continuously monitors Amazon's Business Intelligence & Data Engineering job postings
- **Email Alerts**: Sends personalized notifications when new jobs are posted
- **Job Tracking**: Tracks the top 5 most recent job postings
- **Change Detection**: Identifies new, removed, and position changes in job listings
- **Screenshot Capture**: Takes screenshots for debugging and verification

## Target URL

Monitors: [Amazon Business Intelligence & Data Engineering Jobs](https://amazon.jobs/content/en/job-categories/business-intelligence-data-engineering?country%5B%5D=US&employment-type%5B%5D=Full+time&role-type%5B%5D=0)

## Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd amazon-career-monitoring
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   python setup.py
   ```

4. **Configure email settings** (optional):
   Set environment variables for email notifications:
   ```bash
   export SENDER_EMAIL="your-email@gmail.com"
   export SENDER_PASSWORD="your-app-password"
   export RECIPIENT_EMAILS="recipient1@email.com,recipient2@email.com"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   ```

## Usage

### Manual Run
```bash
python career_monitor.py
```

### GitHub Actions (Automated)
The system is designed to run automatically via GitHub Actions. Set up the following secrets in your repository:

- `SENDER_EMAIL`: Your Gmail address
- `SENDER_PASSWORD`: Your Gmail app password
- `RECIPIENT_EMAILS`: Comma-separated list of recipient emails

## Files Generated

- `career_page_screenshot.png`: Screenshot of the monitored page
- `known_job_counts.json`: Stores previous job counts
- `known_top_jobs.json`: Stores previous top 5 job listings
- `amazon_debug_screenshot.png`: Debug screenshot if job count extraction fails

## Monitoring Details

### Job Categories Monitored
- **Business Intelligence & Data Engineering**: Full-time positions in the US

### Data Tracked
- Total job count changes
- Top 5 most recent job postings
- New job additions
- Job removals
- Position changes in top listings

## Email Notifications

When new jobs are detected, the system sends an email with:
- Number of new jobs posted
- List of top 5 current job postings
- Direct links to view all jobs
- Timestamp of the alert

## Troubleshooting

1. **Job count not detected**: Check the debug screenshot to see the page structure
2. **Email not sending**: Verify environment variables are set correctly
3. **Page loading issues**: Ensure Playwright browser binaries are installed

## Dependencies

- Python 3.7+
- Playwright
- smtplib (built-in)
- json (built-in)

## License

This project is for personal use and educational purposes.
