"""
Integration Pipeline - Connects scraper, LLM intelligence, and database into a unified workflow.

Workflow:
1. Scrape jobs from SAP careers
2. Analyze jobs with LLM and calculate match scores
3. Update job status in database based on match quality
"""

from scraper import setup_driver, scrape_job_listings, extract_job_description, save_job_to_db as scraper_save_job
from intelligence import analyze_and_score_job, MatchScore
from database import Database
import json
import time
import sqlite3


# Job status values for the pipeline
class JobStatus:
    SCRAPED = "scraped"
    ANALYZING = "analyzing"
    MATCHED = "matched"
    HIGH_MATCH = "high_match"
    MEDIUM_MATCH = "medium_match"
    LOW_MATCH = "low_match"
    NO_MATCH = "no_match"


def update_job_match_score(db: Database, job_id: str, match_score: MatchScore):
    """Update a job's status and details in the database based on match score."""
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


def get_unmatched_jobs(db: Database):
    """Get all jobs that haven't been matched yet (status is 'scraped')."""
    with db._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE status = 'scraped' 
            ORDER BY timestamp DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def run_full_pipeline(db: Database, max_jobs: int):
    """Run the complete pipeline: scrape, analyze, and update."""
    print(f"\n{'='*70}")
    print("INTEGRATION PIPELINE - FULL WORKFLOW")
    print(f"{'='*70}")
    
    driver = None
    try:
        # STEP 1: SCRAPE JOBS
        print(f"\n{'='*60}")
        print("STEP 1: SCRAPING JOBS FROM SAP CAREERS")
        print(f"{'='*60}")
        
        driver = setup_driver()
        jobs = scrape_job_listings(driver)
        
        if not jobs:
            print("No jobs found!")
            return False
        
        scraped_count = 0
        for job in jobs[:max_jobs] if max_jobs else jobs:
            details = extract_job_description(driver, job)
            job_data = {
                "url": job[0],
                "title": job[1],
                "job_id": details[0],
                "location": details[1],
                "description": details[2],
            }
            scraper_save_job(db, job_data)
            scraped_count += 1
            time.sleep(1)
        
        print(f"\n✓ Scraped {scraped_count} jobs")
        
        # STEP 2: ANALYZE JOBS WITH LLM
        print(f"\n{'='*60}")
        print("STEP 2: ANALYZING JOBS WITH LLM & CALCULATING MATCH SCORES")
        print(f"{'='*60}")
        
        unmatched_jobs = get_unmatched_jobs(db)
        
        if not unmatched_jobs:
            print("No unmatched jobs to analyze!")
        else:
            print(f"Found {len(unmatched_jobs)} jobs to analyze")
            
            for job in unmatched_jobs:
                print(f"\nAnalyzing: {job['job_title']} ({job['job_id']})")
                
                db.update_job_status(job['job_id'], JobStatus.ANALYZING)
                
                try:
                    match_score = analyze_and_score_job(
                        job_title=job['job_title'],
                        job_id=job['job_id'],
                        location=job['location'],
                        description=job['description']
                    )
                    
                    status = update_job_match_score(db, job['job_id'], match_score)
                    
                    print(f"  → Score: {match_score.overall_score}/100 | Level: {match_score.match_level}")
                    print(f"  → Status: {status}")
                    
                except Exception as e:
                    db.log(f"Error analyzing job {job['job_id']}: {e}", "ERROR")
                    db.update_job_status(job['job_id'], "error")
                
                time.sleep(1)
        
        # STEP 3: SUMMARY
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETE - SUMMARY")
        print(f"{'='*60}")
        
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
            status_counts = cursor.fetchall()
        
        print("\nJobs by status:")
        for status, count in status_counts:
            print(f"  {status}: {count}")
        
        print("\n🎯 High Priority Jobs (ready to apply):")
        with db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_title, location, details FROM jobs 
                WHERE status IN ('high_match', 'medium_match')
                ORDER BY CASE status WHEN 'high_match' THEN 1 WHEN 'medium_match' THEN 2 END
            """)
            priority_jobs = cursor.fetchall()
        
        for job in priority_jobs:
            details = json.loads(job['details']) if job['details'] else {}
            print(f"  • {job['job_title']} - {job['location']} (Score: {details.get('overall_score', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()


def run_analysis_only(db: Database):
    """Run only the analysis step - for jobs that are already scraped but not analyzed."""
    print(f"\n{'='*70}")
    print("ANALYSIS ONLY MODE - Jobs already in DB will be analyzed")
    print(f"{'='*70}")
    
    unmatched_jobs = get_unmatched_jobs(db)
    
    if not unmatched_jobs:
        print("No unmatched jobs to analyze!")
        return
    
    print(f"Found {len(unmatched_jobs)} jobs to analyze\n")
    
    for job in unmatched_jobs:
        print(f"Analyzing: {job['job_title']} ({job['job_id']})")
        
        db.update_job_status(job['job_id'], JobStatus.ANALYZING)
        
        try:
            match_score = analyze_and_score_job(
                job_title=job['job_title'],
                job_id=job['job_id'],
                location=job['location'],
                description=job['description']
            )
            
            status = update_job_match_score(db, job['job_id'], match_score)
            
            print(f"  → Score: {match_score.overall_score}/100 | Level: {match_score.match_level}")
            print(f"  → Status: {status}")
            
        except Exception as e:
            db.log(f"Error analyzing job {job['job_id']}: {e}", "ERROR")
            db.update_job_status(job['job_id'], "error")
        
        time.sleep(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Job Matching Pipeline")
    parser.add_argument("--mode", choices=["full", "analyze"], default="full",
                        help="Run mode: 'full' = scrape + analyze, 'analyze' = only analyze existing jobs")
    parser.add_argument("--max-jobs", type=int, default=None,
                        help="Maximum number of jobs to scrape (default: all)")
    
    args = parser.parse_args()
    
    db = Database()
    
    if args.mode == "full":
        run_full_pipeline(db, max_jobs=args.max_jobs)
    else:
        run_analysis_only(db)
