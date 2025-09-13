#!/usr/bin/env python3
"""
Automated Amazon Career Page Notification System
Monitors Amazon Careers for job count changes and sends email alerts
"""

from playwright.sync_api import sync_playwright
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration variables - Amazon URLs to monitor
TARGET_URLS = {
    "amazon_bi_data_engineering": {
        "url": "https://amazon.jobs/content/en/job-categories/business-intelligence-data-engineering?country%5B%5D=US&employment-type%5B%5D=Full+time&role-type%5B%5D=0",
        "name": "Amazon Business Intelligence & Data Engineering Jobs",
        "selector": "span[data-testid='job-count']"  # Will need to be updated based on actual page structure
    }
}

SCREENSHOT_PATH = "career_page_screenshot.png"
KNOWN_JOBS_FILE = "known_job_counts.json"  # JSON for multiple URLs
KNOWN_TOP_JOBS_FILE = "known_top_jobs.json"  # Track top 5 jobs for each category

# Email configuration (will be set via environment variables in GitHub Actions)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
RECIPIENT_EMAILS = os.getenv('RECIPIENT_EMAILS', '')  # Comma-separated list of emails

def extract_job_count(page, selector):
    """Extract the total job count from the Amazon career page"""
    print("Extracting job count...")
    
    try:
        # Wait for the page to load completely
        page.wait_for_load_state("networkidle")
        
        # Try multiple selectors that might contain job count
        selectors_to_try = [
            "span[data-testid='job-count']",
            ".job-count",
            "[data-testid*='count']",
            "span:contains('jobs')",
            "div:contains('jobs')",
            "span:contains('openings')",
            "div:contains('openings')",
            "span:contains('positions')",
            "div:contains('positions')"
        ]
        
        job_count = None
        for sel in selectors_to_try:
            try:
                if ":contains" in sel:
                    # Handle text-based selectors differently
                    elements = page.query_selector_all("*")
                    for element in elements:
                        text = element.inner_text().strip().lower()
                        if "job" in text and any(char.isdigit() for char in text):
                            # Extract number from text
                            import re
                            numbers = re.findall(r'\d+', text)
                            if numbers:
                                job_count = int(numbers[0])
                                print(f"Found job count using text search: {job_count}")
                                break
                else:
                    # Try CSS selector
                    element = page.query_selector(sel)
                    if element:
                        text = element.inner_text().strip()
                        print(f"Raw text from selector '{sel}': '{text}'")
                        if text and any(char.isdigit() for char in text):
                            import re
                            numbers = re.findall(r'\d+', text)
                            if numbers:
                                job_count = int(numbers[0])
                                print(f"Found job count using selector '{sel}': {job_count}")
                                break
            except Exception as e:
                print(f"Error with selector '{sel}': {str(e)}")
                continue
        
        if job_count is not None:
            print(f"Successfully extracted job count: {job_count}")
            return job_count
        else:
            print("Could not find job count using any selector")
            # Take a screenshot for debugging
            page.screenshot(path="amazon_debug_screenshot.png")
            print("Debug screenshot saved as amazon_debug_screenshot.png")
            return None
            
    except Exception as e:
        print(f"Error extracting job count: {str(e)}")
        return None

def load_known_job_counts():
    """Load the last known job counts from file"""
    try:
        if os.path.exists(KNOWN_JOBS_FILE):
            with open(KNOWN_JOBS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading known job counts: {str(e)}")
        return {}

def save_job_counts(counts):
    """Save the current job counts to file"""
    try:
        with open(KNOWN_JOBS_FILE, 'w') as f:
            json.dump(counts, f, indent=2)
        print(f"Saved job counts to {KNOWN_JOBS_FILE}")
    except Exception as e:
        print(f"Error saving job counts: {str(e)}")

def extract_top_jobs(page, max_jobs=5):
    """Extract top job titles from the Amazon career page"""
    try:
        # Try multiple selectors for job titles
        selectors_to_try = [
            "h3[data-testid*='job-title']",
            "h3.job-title",
            "a[data-testid*='job-title']",
            "a.job-title",
            "h3",
            "h2",
            "a[href*='/jobs/']",
            ".job-title",
            "[data-testid*='title']"
        ]
        
        jobs = []
        for selector in selectors_to_try:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    job_title = element.inner_text().strip()
                    if job_title and len(job_title) > 5 and len(job_title) < 200:  # Basic validation
                        # Filter out common non-job elements
                        if not any(skip in job_title.lower() for skip in ['search', 'filter', 'sort', 'apply', 'browse', 'view all']):
                            jobs.append(job_title)
                            if len(jobs) >= max_jobs:
                                break
                if jobs:
                    break
            except Exception as e:
                print(f"Error with selector '{selector}': {str(e)}")
                continue
        
        print(f"Extracted {len(jobs)} job titles")
        return jobs[:max_jobs]  # Return only top 5
        
    except Exception as e:
        print(f"Error extracting job titles: {str(e)}")
        return []

def load_known_top_jobs():
    """Load previously known top jobs from JSON file"""
    try:
        if os.path.exists(KNOWN_TOP_JOBS_FILE):
            with open(KNOWN_TOP_JOBS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading known top jobs: {str(e)}")
        return {}

def save_top_jobs(top_jobs):
    """Save top jobs to JSON file"""
    try:
        with open(KNOWN_TOP_JOBS_FILE, 'w') as f:
            json.dump(top_jobs, f, indent=2)
        print(f"Saved top jobs to {KNOWN_TOP_JOBS_FILE}")
    except Exception as e:
        print(f"Error saving top jobs: {str(e)}")

def compare_top_jobs(current_jobs, previous_jobs, source_name):
    """Compare current and previous top jobs and return changes"""
    changes = []
    
    if not previous_jobs:
        # First run - all jobs are new
        for job in current_jobs:
            changes.append({
                'action': 'new',
                'job_title': job,
                'position': current_jobs.index(job) + 1
            })
        return changes
    
    # Check for new jobs
    for i, job in enumerate(current_jobs):
        if job not in previous_jobs:
            changes.append({
                'action': 'new',
                'job_title': job,
                'position': i + 1
            })
    
    # Check for removed jobs
    for job in previous_jobs:
        if job not in current_jobs:
            changes.append({
                'action': 'removed',
                'job_title': job,
                'position': previous_jobs.index(job) + 1
            })
    
    # Check for position changes
    for i, job in enumerate(current_jobs):
        if job in previous_jobs:
            old_position = previous_jobs.index(job) + 1
            new_position = i + 1
            if old_position != new_position:
                changes.append({
                    'action': 'moved',
                    'job_title': job,
                    'old_position': old_position,
                    'new_position': new_position
                })
    
    return changes

def send_email_alert(changes, job_changes=None, current_top_jobs=None):
    """Send personalized email alert when job counts change or top jobs change"""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAILS]):
        print("Email configuration incomplete. Skipping email alert.")
        return False
    
    # Parse recipient emails (comma-separated)
    recipient_list = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]
    if not recipient_list:
        print("No valid recipient emails found. Skipping email alert.")
        return False
    
    try:
        # Filter to only show categories with new jobs (increases)
        categories_with_new_jobs = {k: v for k, v in changes.items() if v['current'] > v['previous']}
        
        if not categories_with_new_jobs:
            print("No categories with new jobs found. Skipping email alert.")
            return False
        
        # Create personalized subject based on what changed
        if len(categories_with_new_jobs) == 1:
            source_name = list(categories_with_new_jobs.values())[0]['name']
            change = list(categories_with_new_jobs.values())[0]['current'] - list(categories_with_new_jobs.values())[0]['previous']
            subject = f"🚨 {source_name}: {change} new jobs posted!"
        else:
            total_new_jobs = sum(data['current'] - data['previous'] for data in categories_with_new_jobs.values())
            subject = f"🚨 {len(categories_with_new_jobs)} categories: {total_new_jobs} new jobs posted!"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipient_list)  # Show all recipients in To field
        msg['Subject'] = subject
        
        # Build personalized email body
        body = "🎯 Amazon Careers Job Monitoring Alert\n"
        body += "=" * 50 + "\n\n"
        body += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Add total new jobs count
        total_new_jobs = sum(data['current'] - data['previous'] for data in categories_with_new_jobs.values())
        body += f"🎉 {total_new_jobs} new job(s) posted across {len(categories_with_new_jobs)} categories!\n\n"
        
        # Show only categories with new jobs and their top 5 roles
        for source_key, data in categories_with_new_jobs.items():
            change = data['current'] - data['previous']
            body += f"📋 {data['name']} (+{change} jobs)\n"
            body += "-" * 40 + "\n"
            
            # Get the current top 5 jobs for this category
            if current_top_jobs and source_key in current_top_jobs:
                top_jobs = current_top_jobs[source_key]
                for i, job_title in enumerate(top_jobs, 1):
                    body += f"   {i}. {job_title}\n"
            else:
                body += "   (Top jobs not available)\n"
            
            body += f"\n   🔗 View all jobs: {data['url']}\n\n"
        
        body += "🤖 This is an automated alert from your Amazon career monitoring system.\n"
        body += "💡 Set up job alerts on Amazon Careers for instant notifications!"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email to all recipients
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_list, text)
        server.quit()
        
        print(f"📧 Personalized email alert sent to {len(recipient_list)} recipient(s)! {len(categories_with_new_jobs)} category(ies) with new jobs.")
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def main():
    """Main function to monitor Amazon job sources and send alerts"""
    print("Starting Amazon career monitoring system...")
    print(f"Monitoring {len(TARGET_URLS)} job sources:")
    for key, config in TARGET_URLS.items():
        print(f"  • {config['name']}")
    
    try:
        with sync_playwright() as p:
            # Launch browser
            print("\nLaunching browser...")
            browser = p.chromium.launch(headless=True)  # Headless for GitHub Actions
            page = browser.new_page()
            
            # Load previous job counts and top jobs
            known_counts = load_known_job_counts()
            known_top_jobs = load_known_top_jobs()
            current_counts = {}
            current_top_jobs = {}
            changes = {}
            increases = {}  # Track only increases for email alerts
            job_changes = {}  # Track changes in top jobs
            
            # Monitor each URL
            for source_key, config in TARGET_URLS.items():
                print(f"\n--- Monitoring {config['name']} ---")
                print(f"URL: {config['url']}")
                
                try:
                    # Navigate to the URL
                    page.goto(config['url'], wait_until="networkidle")
                    
                    # Take a screenshot for debugging
                    page.screenshot(path=SCREENSHOT_PATH)
                    print(f"Screenshot saved as {SCREENSHOT_PATH}")
                    
                    # Extract job count
                    current_count = extract_job_count(page, config['selector'])
                    
                    if current_count is None:
                        print(f"Failed to extract job count for {config['name']}")
                        # Still try to extract top jobs even if count fails
                        current_count = 0
                    
                    current_counts[source_key] = current_count
                    previous_count = known_counts.get(source_key)
                    
                    print(f"Current count: {current_count}")
                    
                    # Extract top 5 jobs
                    print("Extracting top 5 jobs...")
                    current_jobs = extract_top_jobs(page)
                    current_top_jobs[source_key] = current_jobs
                    
                    # Compare with previous top jobs
                    previous_jobs = known_top_jobs.get(source_key, [])
                    job_changes_list = compare_top_jobs(current_jobs, previous_jobs, config['name'])
                    
                    if job_changes_list:
                        job_changes[config['name']] = job_changes_list
                        print(f"Job changes detected: {len(job_changes_list)} changes")
                        for change in job_changes_list:
                            if change['action'] == 'new':
                                print(f"  🆕 New: #{change['position']} {change['job_title']}")
                            elif change['action'] == 'removed':
                                print(f"  ❌ Removed: {change['job_title']}")
                            elif change['action'] == 'moved':
                                print(f"  🔄 Moved: {change['job_title']} (#{change['old_position']} → #{change['new_position']})")
                    else:
                        print("No job changes detected in top 5")
                    
                    if previous_count is None:
                        # First run for this source
                        print(f"First run for {config['name']}. Saving initial count.")
                    else:
                        print(f"Previous count: {previous_count}")
                        
                        if current_count != previous_count:
                            # Job count changed
                            change = current_count - previous_count
                            change_text = f"+{change}" if change > 0 else str(change)
                            print(f"Job count changed! {previous_count} → {current_count} ({change_text})")
                            
                            # Record the change
                            changes[source_key] = {
                                'name': config['name'],
                                'url': config['url'],
                                'previous': previous_count,
                                'current': current_count
                            }
                            
                            # Track increases separately for email alerts
                            if current_count > previous_count:
                                increases[source_key] = changes[source_key]
                        else:
                            print("No changes detected.")
                
                except Exception as e:
                    print(f"Error monitoring {config['name']}: {str(e)}")
                    continue
            
            # Close browser
            browser.close()
            
            # Send email if there were increases
            if increases:
                print(f"\n📧 Sending email alert...")
                print(f"  • {len(increases)} source(s) with increased job counts")
                
                if send_email_alert(increases, job_changes, current_top_jobs):
                    print("Email alert sent successfully!")
                else:
                    print("Failed to send email alert.")
            elif changes:
                print(f"\n📊 {len(changes)} source(s) changed but no increases detected. No email sent.")
            else:
                print("\n✅ No changes detected across all sources.")
            
            # Update stored counts and top jobs
            save_job_counts(current_counts)
            save_top_jobs(current_top_jobs)
            
            print("\n🎯 Amazon career monitoring completed successfully!")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("Script completed successfully!")
    else:
        print("Script failed!")
