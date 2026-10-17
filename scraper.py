"""
SAP Job Scraper - Collects job listings and extracts descriptions to feed to a local LLM to evaluate my chances of getting this job

"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from urllib.parse import urljoin
from database import Database
import time
from intelligence import analyze_and_score_job, get_job_details,MatchScore, Job 
import json
import sqlite3

class JobStatus:
    SCRAPED = "scraped"
    ANALYZING = "analyzing"
    MATCHED = "matched"
    HIGH_MATCH = "high_match"
    MEDIUM_MATCH = "medium_match"
    LOW_MATCH = "low_match"
    NO_MATCH = "no_match"

# Create and update browser settings either headless or anything else
def setup_driver(): 
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--ozone-platform=x11")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Accept or reject cookies ... depending on the needs of the user
def reject_cookies(driver):
    try:
        wait = WebDriverWait(driver, 5)
        reject_button = wait.until(
            EC.element_to_be_clickable((By.ID, "truste-consent-required"))
        )
        reject_button.click()
        print("Cookie consent rejected")
        time.sleep(1)
    except:
        print("Cookie dialog handled")

# Get a list of all jobs and explore each job one after the other... 
def scrape_job_listings(driver):
    """Scrape job listings from SAP careers search results"""
    url = (
        "https://careers.sap.com/search/?"
        "createNewAlert=false&q=&locationsearch=walldorf%2C+munich"
        "&optionsFacetsDD_department=&optionsFacetsDD_customfield3=Student"
        "&optionsFacetsDD_country=DE"
    )
    print(f"\n{'='*60}")
    print("STEP 1: SCRAPING JOB LISTINGS")
    print(f"{'='*60}")
    print(f"Navigating to: {url}")
    
    driver.get(url)
    time.sleep(5)
    reject_cookies(driver)
    time.sleep(3)
    
    job_elements = []    
    counter = 0
    # Strategy 2: Direct link search
    if not job_elements:
        print("\nTrying direct link search...")
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.data-row")

        for row in rows:
            link_element = row.find_element(
                By.CSS_SELECTOR, "a.jobTitle-link"
            )
            job_title = link_element.text.strip()
            job_link = urljoin(driver.current_url, link_element.get_attribute("href"))
            description = ""
            job = [job_link, job_title,description]
            job_elements.append(job)
            print(job)
            counter += 1
            if counter > 1 :
                break
            
    print(f"\n{'='*60}")
    print(f"EXTRACTING DATA FROM {len(job_elements)} JOBS")
    print(f"{'='*60}\n")
    return job_elements

# Extract job details to feed to the AI ...
def extract_job_description(driver, job):
    job_url = job[0]
    details = []
    wait = WebDriverWait(driver, 10)

    existing_handles = driver.window_handles
    # Open the job page in a new tab
    driver.execute_script(
        "window.open(arguments[0], '_blank');",
        job_url
    )
    # Wait for the new tab and switch to it
    wait.until(EC.number_of_windows_to_be(len(existing_handles) + 1))
    new_handle = next(
        handle for handle in driver.window_handles
        if handle not in existing_handles
    )
    driver.switch_to.window(new_handle)
   
    try:
        job_id_element = wait.until(
            EC.visibility_of_element_located(
            (By.XPATH,"//span[@class='joblayouttoken-label' and contains(normalize-space(), 'Requisition ID')]"))
        )
        job_id = job_id_element.find_element(
            By.XPATH, "following-sibling::span[1]"
        ).text.strip()
        location_element = driver.find_element(
            By.XPATH,
            "//span[normalize-space()='Location']/following-sibling::span[1]//span[@class='jobGeoLocation']"
        )
        location = location_element.text.strip()
        details.append(job_id)
        details.append(location)
    except NoSuchElementException:
        print("not found")
    finally:
        description = "\n".join(
            li.text.strip()
            for li in driver.find_elements(By.CSS_SELECTOR, "ul li")
            if li.text.strip())
        details.append(description)
    time.sleep(3)
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(2)
  
    return details

# Once the job is evaluated by the model ... it can be saved to the database as a match 
def save_job_to_db(db, job_data):
    db.add_job(
        job_url=job_data["url"],
        job_id=job_data["job_id"],
        status="scraped",
        job_title=job_data["title"],
        location=job_data["location"],
        description=job_data["description"]
    )

# Update a job's status and details in the database based on match score.
def update_job_match_score(db: Database, job_id: str, match_score: MatchScore):
    status_map = {
        "high": JobStatus.HIGH_MATCH,
        "medium": JobStatus.MEDIUM_MATCH,
        "low": JobStatus.LOW_MATCH,
        "no_match": JobStatus.NO_MATCH
    }
    status = status_map.get(match_score.match_level, JobStatus.MATCHED)
    
    details = json.dumps({
        "overall_score": match_score.overall_score,
        "match_level": match_score.match_level,
        "matched_requirements": match_score.matched_requirements,
        "missing_required": match_score.missing_required,
        "missing_preferred": match_score.missing_preferred,
        "analysis_notes": match_score.analysis_notes
    })
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, details = ?, timestamp = datetime('now')
            WHERE job_id = ?
        """, (status, details, job_id))
        conn.commit()
    
    db.log(f"Job {job_id} updated: {status} (score: {match_score.overall_score})", "INFO")
    return status

# Get all jobs that haven't been matched yet (status is 'scraped').
def get_unmatched_jobs(db: Database):
    with db._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE status = 'scraped' 
            ORDER BY timestamp DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

# Run only the analysis step - for jobs that are already scraped but not analyzed.
def run_analysis_only(db: Database):
    print(f"\n{'='*70}")
    print("ANALYSIS ONLY MODE - Jobs already in DB will be analyzed")
    print(f"{'='*70}")
    
    unmatched_jobs = get_unmatched_jobs(db)
    
    if not unmatched_jobs:
        print("No unmatched jobs to analyze!")
        return
    
    print(f"Found {len(unmatched_jobs)} jobs to analyze\n")
    
    for job in unmatched_jobs:   
        db.update_job_status(job['job_id'], JobStatus.ANALYZING)
        try:
            job_object = Job(
                title = job["title"],
                job_id = job["job_id"],
                location = job["location"],
                description = job["description"],
            )
            match_score = analyze_and_score_job(job_object,job["details"])
                    
            status = update_job_match_score(db, job['job_id'], match_score)
            
            print(f"  → Score: {match_score.overall_score}/100 | Level: {match_score.match_level}")
            print(f"  → Status: {status}")
            
        except Exception as e:
            db.log(f"Error analyzing job {job['job_id']}: {e}", "ERROR")
            db.update_job_status(job['job_id'], "error")
        
        time.sleep(1)

# Main function... 
def main():
    """
Integration Pipeline - Connects scraper, LLM intelligence, and database into a unified workflow.

Workflow:
1. Scrape jobs from SAP careers
2. Analyze jobs with LLM and calculate match scores
3. Update job status in database based on match quality
"""
    print(f"{'='*60}")
    print("SAP JOB SCRAPER")
    print(f"{'='*60}")
    
    driver = setup_driver()
    db = Database()
    
    try:
        jobs = scrape_job_listings(driver)
        if not jobs:
            print("No jobs found!")
            driver.save_screenshot("/tmp/scraper_debug.png")
            return False
        print(f"\n{'='*60}")
        print("STEP 2: EXTRACTING DESCRIPTIONS")
        print(f"{'='*60}\n")

        for job in jobs:
            details = extract_job_description(driver,job)
            time.sleep(1)
            job_data = {
                "url": job[0],
                "title": job[1],
                "job_id":details[0],
                "location": details[1],
                "description": details[2],
            }
            save_job_to_db(db, job_data)
            
            job_object = Job(
                title = job_data["title"],
                job_id = job_data["job_id"],
                location = job_data["location"],
                description = job_data["description"],
            )
            job_detail = get_job_details(job_object)
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs 
                    SET details = ?
                    WHERE job_id = ?
                """, ( job_detail, job_data["job_id"]))
                conn.commit()

        unmatched_jobs = get_unmatched_jobs(db)

        if not unmatched_jobs:
            print("No unmatched jobs to analyze!")
        else:
            print(f"Found {len(unmatched_jobs)} jobs to analyze")
            
            for j in unmatched_jobs:                
                #db.update_job_status(job['job_id'], JobStatus.ANALYZING)
                try:
                    job_object = Job(
                        title = j["job_title"],
                        job_id = j["job_id"],
                        location = j["location"],
                        description = j["description"],
                    )
                    json_details = json.loads(j["details"])
                    match_score = analyze_and_score_job(job_object,json_details)
                    
                    status = update_job_match_score(db, j['job_id'], match_score)
                    
                    print(f"  → Score: {match_score.overall_score}/100 | Level: {match_score.match_level}")
                    print(f"  → Status: {status}")
                    
                except Exception as e:
                    db.log(f"Error analyzing job {j['job_id']}: {e}", "ERROR")
                    db.update_job_status(j['job_id'], "error")
                
                time.sleep(1) 
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()


