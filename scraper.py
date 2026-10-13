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
            job = [job_link, job_title]
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

# Main function... 
def main():
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
            job_data = {
                "url": job[0],
                "title": job[1],
                "job_id":details[0],
                "location": details[1],
                "description": details[2],
            }
            save_job_to_db(db, job_data)
            time.sleep(1)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
