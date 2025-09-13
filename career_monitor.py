#!/usr/bin/env python3
"""
Automated Amazon Career Page Notification System
Monitors Amazon Careers for jobs updated today and sends email alerts
"""

from playwright.sync_api import sync_playwright
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import re

# Configuration variables - Amazon URLs to monitor
TARGET_URLS = {
    "amazon_bi_data_engineering": {
        "url": "https://amazon.jobs/content/en/job-categories/business-intelligence-data-engineering?country%5B%5D=US&employment-type%5B%5D=Full+time&role-type%5B%5D=0",
        "name": "Amazon Business Intelligence & Data Engineering Jobs"
    }
}

SCREENSHOT_PATH = "career_page_screenshot.png"
KNOWN_TODAYS_JOBS_FILE = "known_todays_jobs.json"  # Track jobs updated today

# Email configuration (will be set via environment variables in GitHub Actions)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
RECIPIENT_EMAILS = os.getenv('RECIPIENT_EMAILS', '')  # Comma-separated list of emails

def extract_todays_jobs(page):
    """Extract jobs that were updated today from the Amazon career page"""
    print("Extracting jobs updated today...")
    
    try:
        # Wait for the page to load completely
        page.wait_for_load_state("domcontentloaded")
        
        # Get today's date in the format used by Amazon (M/D/YYYY)
        today = date.today()
        today_formatted = f"{today.month}/{today.day}/{today.year}"
        print(f"Looking for jobs updated on: {today_formatted}")
        
        # Find all job elements that contain "Updated:" text
        updated_elements = page.query_selector_all('div[data-test-component="StencilText"]')
        print(f"Found {len(updated_elements)} elements with StencilText component")
        
        todays_jobs = []
        
        # Look for job containers using the specific structure we found
        print("Looking for job containers with the correct structure...")
        
        # Look for job containers that have the header structure
        job_containers = page.query_selector_all('div[class*="header-module_root"]')
        print(f"Found {len(job_containers)} job containers with header structure")
        
        for i, container in enumerate(job_containers):
            try:
                container_text = container.inner_text()
                if "Updated:" in container_text and today_formatted in container_text:
                    print(f"Found job container {i} with today's date")
                    
                    # Look for job title in h3 > a element (the specific structure we found)
                    title_element = container.query_selector('h3 a')
                    if title_element:
                        job_title = title_element.inner_text().strip()
                        if job_title and len(job_title) > 5:
                            job_info = {
                                'title': job_title,
                                'updated_date': today_formatted,
                                'element_text': f"Found in container {i}"
                            }
                            todays_jobs.append(job_info)
                            print(f"Found job updated today: {job_title}")
                        else:
                            print(f"Job title too short or empty in container {i}")
                    else:
                        print(f"Could not find h3 a element in container {i}")
            except Exception as e:
                print(f"Error processing container {i}: {str(e)}")
                continue
        
        # If the container approach didn't work, try the original approach
        if not todays_jobs:
            print("Container approach didn't work, trying original approach...")
            for i, element in enumerate(updated_elements):
                try:
                    text = element.inner_text().strip()
                    
                    if "Updated:" in text and today_formatted in text:
                        print(f"Found 'Updated:' in element {i}")
                        # This is a job updated today, find the job title
                        job_title = find_job_title_near_element(element, page)
                        if job_title:
                            job_info = {
                                'title': job_title,
                                'updated_date': today_formatted,
                                'element_text': text
                            }
                            todays_jobs.append(job_info)
                            print(f"Found job updated today: {job_title}")
                        else:
                            print(f"Could not find job title for element {i}")
                except Exception as e:
                    print(f"Error processing element {i}: {str(e)}")
                    continue
        
        print(f"Found {len(todays_jobs)} jobs updated today")
        return todays_jobs
        
    except Exception as e:
        print(f"Error extracting today's jobs: {str(e)}")
        return []

def find_job_title_near_element(updated_element, page):
    """Find the job title near the updated date element"""
    try:
        # First, let's look at the HTML structure around the updated element
        print("Examining HTML structure around updated element...")
        
        # Get the parent container that likely contains the job listing
        parent = updated_element
        for level in range(15):  # Go up to 15 levels up
            if parent is None:
                break
            
            # Get the HTML of the current parent to understand structure
            try:
                parent_html = parent.inner_html()
                if len(parent_html) > 1000:  # Only print if it's a substantial container
                    print(f"Level {level} parent HTML (first 500 chars): {parent_html[:500]}")
            except:
                pass
            
            # Look for job title in current level and all descendants
            title_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'a[href*="/jobs/"]', 
                'a[href*="/job/"]',
                '.job-title', 
                '[data-testid*="title"]',
                '[data-testid*="job-title"]',
                'span[data-testid*="title"]',
                'div[data-testid*="title"]',
                'a[data-testid*="job"]',
                'div[data-testid*="job"]'
            ]
            
            for selector in title_selectors:
                try:
                    # Look in current element
                    title_element = parent.query_selector(selector)
                    if title_element:
                        title_text = title_element.inner_text().strip()
                        if title_text and len(title_text) > 5 and len(title_text) < 200:
                            # Filter out common non-job elements
                            if not any(skip in title_text.lower() for skip in ['search', 'filter', 'sort', 'apply', 'browse', 'view all', 'updated:', 'date:', 'location:', 'read more']):
                                print(f"Found job title at level {level} with selector '{selector}': {title_text}")
                                return title_text
                    
                    # Look in all descendants
                    title_elements = parent.query_selector_all(selector)
                    for element in title_elements:
                        title_text = element.inner_text().strip()
                        if title_text and len(title_text) > 5 and len(title_text) < 200:
                            if not any(skip in title_text.lower() for skip in ['search', 'filter', 'sort', 'apply', 'browse', 'view all', 'updated:', 'date:', 'location:', 'read more']):
                                print(f"Found job title in descendant at level {level} with selector '{selector}': {title_text}")
                                return title_text
                except Exception as e:
                    continue
            
            # Look for any text that might be a job title (fallback)
            try:
                all_text_elements = parent.query_selector_all('*')
                for element in all_text_elements:
                    text = element.inner_text().strip()
                    if text and len(text) > 10 and len(text) < 200:
                        # Check if it looks like a job title
                        if any(keyword in text.lower() for keyword in ['engineer', 'analyst', 'manager', 'specialist', 'developer', 'scientist', 'architect', 'consultant', 'director', 'lead', 'senior', 'principal', 'business intelligence', 'data']):
                            if not any(skip in text.lower() for skip in ['search', 'filter', 'sort', 'apply', 'browse', 'view all', 'updated:', 'date:', 'location:', 'job', 'career', 'amazon', 'read more', 'usa']):
                                print(f"Found potential job title by keyword matching: {text}")
                                return text
            except:
                pass
            
            # Move to parent element
            try:
                parent = parent.evaluate('el => el.parentElement')
            except:
                break
        
        print("Could not find job title near updated element")
        return None
    except Exception as e:
        print(f"Error finding job title: {str(e)}")
        return None

def load_known_todays_jobs():
    """Load previously known today's jobs from JSON file"""
    try:
        if os.path.exists(KNOWN_TODAYS_JOBS_FILE):
            with open(KNOWN_TODAYS_JOBS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading known today's jobs: {str(e)}")
        return {}

def save_todays_jobs(todays_jobs):
    """Save today's jobs to JSON file"""
    try:
        with open(KNOWN_TODAYS_JOBS_FILE, 'w') as f:
            json.dump(todays_jobs, f, indent=2)
        print(f"Saved today's jobs to {KNOWN_TODAYS_JOBS_FILE}")
    except Exception as e:
        print(f"Error saving today's jobs: {str(e)}")

def compare_todays_jobs(current_jobs, previous_jobs, source_name):
    """Compare current and previous today's jobs and return new jobs"""
    new_jobs = []
    
    if not previous_jobs:
        # First run - all jobs are new
        for job in current_jobs:
            new_jobs.append({
                'action': 'new',
                'job_title': job['title'],
                'updated_date': job['updated_date']
            })
        return new_jobs
    
    # Get previous job titles for comparison
    previous_titles = [job['title'] for job in previous_jobs]
    
    # Check for new jobs
    for job in current_jobs:
        if job['title'] not in previous_titles:
            new_jobs.append({
                'action': 'new',
                'job_title': job['title'],
                'updated_date': job['updated_date']
            })
    
    return new_jobs

def send_email_alert(new_jobs, source_name, source_url):
    """Send email alert when new jobs updated today are found"""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAILS]):
        print("Email configuration incomplete. Skipping email alert.")
        return False
    
    # Parse recipient emails (comma-separated)
    recipient_list = [email.strip() for email in RECIPIENT_EMAILS.split(',') if email.strip()]
    if not recipient_list:
        print("No valid recipient emails found. Skipping email alert.")
        return False
    
    if not new_jobs:
        print("No new jobs found. Skipping email alert.")
        return False
    
    try:
        # Create personalized subject
        job_count = len(new_jobs)
        if job_count == 1:
            subject = f"🚨 Amazon: 1 new job updated today!"
        else:
            subject = f"🚨 Amazon: {job_count} new jobs updated today!"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipient_list)
        msg['Subject'] = subject
        
        # Build personalized email body
        body = "🎯 Amazon Careers - Jobs Updated Today Alert\n"
        body += "=" * 50 + "\n\n"
        body += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        body += f"📋 {source_name}\n"
        body += f"📅 Updated: {date.today().strftime('%B %d, %Y')}\n\n"
        
        body += f"🎉 {job_count} new job(s) updated today!\n\n"
        
        # List the new jobs
        for i, job in enumerate(new_jobs, 1):
            body += f"   {i}. {job['job_title']}\n"
            body += f"      📅 Updated: {job['updated_date']}\n\n"
        
        body += f"🔗 View all jobs: {source_url}\n\n"
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
        
        print(f"📧 Email alert sent to {len(recipient_list)} recipient(s)! {job_count} new job(s) found.")
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
            
            # Load previous today's jobs
            known_todays_jobs = load_known_todays_jobs()
            current_todays_jobs = {}
            all_new_jobs = []
            
            # Monitor each URL
            for source_key, config in TARGET_URLS.items():
                print(f"\n--- Monitoring {config['name']} ---")
                print(f"URL: {config['url']}")
                
                try:
                    # Navigate to the URL with longer timeout and different wait strategy
                    print("Navigating to Amazon careers page...")
                    page.goto(config['url'], timeout=60000, wait_until="domcontentloaded")
                    
                    # Wait a bit more for dynamic content
                    page.wait_for_timeout(5000)
                    
                    # Take a screenshot for debugging
                    page.screenshot(path=SCREENSHOT_PATH)
                    print(f"Screenshot saved as {SCREENSHOT_PATH}")
                    
                    # Extract jobs updated today
                    current_jobs = extract_todays_jobs(page)
                    current_todays_jobs[source_key] = current_jobs
                    
                    print(f"Found {len(current_jobs)} jobs updated today")
                    
                    # Compare with previous today's jobs
                    previous_jobs = known_todays_jobs.get(source_key, [])
                    new_jobs = compare_todays_jobs(current_jobs, previous_jobs, config['name'])
                    
                    if new_jobs:
                        all_new_jobs.extend(new_jobs)
                        print(f"New jobs detected: {len(new_jobs)} new jobs")
                        for job in new_jobs:
                            print(f"  🆕 New: {job['job_title']}")
                    else:
                        print("No new jobs updated today")
                
                except Exception as e:
                    print(f"Error monitoring {config['name']}: {str(e)}")
                    continue
            
            # Close browser
            browser.close()
            
            # Send email if there were new jobs
            if all_new_jobs:
                print(f"\n📧 Sending email alert...")
                print(f"  • {len(all_new_jobs)} new job(s) found")
                
                # Send alert for the first source (assuming single source for now)
                source_key = list(TARGET_URLS.keys())[0]
                source_config = TARGET_URLS[source_key]
                
                if send_email_alert(all_new_jobs, source_config['name'], source_config['url']):
                    print("Email alert sent successfully!")
                else:
                    print("Failed to send email alert.")
            else:
                print("\n✅ No new jobs updated today.")
            
            # Update stored today's jobs
            save_todays_jobs(current_todays_jobs)
            
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
