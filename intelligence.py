from ollama import chat
from pydantic import BaseModel,Field
from typing import Literal

from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
class Job(BaseModel):
    title: str
    job_id: int 
    location: str
    description: str

class Requirement(BaseModel):
    name: str
    status: Literal["required", "preferred", "unknown"]
class Requirements(BaseModel):
    education: list[Requirement] = Field(
        description="Educational qualifications explicitly mentioned in the job description."
    )

    technical_skills: list[Requirement] = Field(
        description="Technical abilities or knowledge required or preferred for the job."
    )

    experience: list[Requirement] = Field(
        description="Previous work experience explicitly mentioned in the job description."
    )

    technologies: list[Requirement] = Field(
        description="Specific software, platforms, programming languages, tools, or technologies."
    )

    skills: list[Requirement] = Field(
        description="Professional or soft skills such as analytical thinking, teamwork, communication, and problem solving."
    )

    languages: list[Requirement] = Field(
        description="Human languages such as English, German, French, etc."
    )

class CandidateProfile(BaseModel):
    education: list[str]
    technical_skills: list[str]
    technologies: list[str]
    skills: list[str]
    languages: list[str]
    experience: list[str]
    certifications: list[str]
    projects: list[str]

candidate = CandidateProfile(
    education=[
        "Bachelorstudium Robotik at Technische Hochschule Würzburg-Schweinfurt",
        #'Dual Bachelorstudium Informatik (SAP "KI") at DHBW Mosbach - Walldorf',
        "Abitur at Government Bilingual High School Bafoussam"
    ],

    technical_skills=[
        "Object-Oriented Programming",
        "Algorithm Engineering",
        "Programming",
        "Electrical Engineering",
        "AI and Automation",
        "REST APIs",
        "Database integration",
        "Software engineering",
        "Web development"
    ],

    technologies=[
        "C++",
        "python3",
        "JavaScript",
        "Selenium",
        "Git",
        "GitHub",
        "Linux",
        "Ubuntu",
        "Bash",
        "Svelte",
        "Bootstrap",
        "Tailwind CSS",
        "Astro",
        "React",
        "PocketBase",
        "Microsoft 365",
        "Excel",
        "PowerPoint",
        "SharePoint",
        "Outlook",
        "Cline",
        "Cursor",
        "ChatGPT",
        "Gemini",
        "GitHub Copilot"
    ],

    skills=[
        "Analytical thinking",
        "Problem solving",
        "Teamwork",
        "Creativity",
        "Reliability",
        "Flexibility",
        "Independent work",
        "Learning new technologies"
    ],

    languages=[
        "German",
        "English",
        "French"
    ],

    experience=[
        "Software development of a commercial online marketplace",
        "Frontend development with Astro and React",
        "Backend development with PocketBase",
        "Authentication and database implementation",
        "REST API development",
        "Collaborative software development using Git",
        "Branch management",
        "Merge conflict resolution",
        "Code reviews",
        "Python and Pygame development",
        "Modular software architecture",
        "Development of an automated job search and application system",
        "Automatic form filling and application submission",
        "Database storage and filtering of job offers",
        "Email forwarding of unsuitable job offers"
    ],

    certifications=[
        "Python - 100 Days of Code Challenge from Udemy (76 days completed)",
        "Developing Regression Models with the Python Machine Learning Client for SAP HANA",
        "Python Basic Certificate - HackerRank",
        "Problem Solving Basic - HackerRank"
    ],

    projects=[
        "petit Market - Online marketplace platform",
        "Chess game with Python and Pygame",
        "Jobruf - Automated job search and application tool"
    ]
)
class Job_validation(BaseModel):
  category: str
  job_types: list[str]
  requirements: Requirements
class MatchScore(BaseModel):
    """Score result for a job vs candidate profile matching"""
    job_id: int
    overall_score: int  # 0-100
    match_level: Literal["high", "medium", "low", "no_match"]
    matched_requirements: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    analysis_notes: str

def get_candidate_profile() -> CandidateProfile:
    """Return the global candidate profile"""
    return candidate

def calculate_match_score(job_analysis: Job_validation, candidate_profile: CandidateProfile, job_id: int) -> MatchScore:
    # Calculate how well a job matches the candidate profile based on the LLM analysis.
    matched = []
    missing_required = []
    missing_preferred = []
    
    def check_match(requirement_name: str, candidate_items: list[str]) -> bool:
        req_lower = requirement_name.lower()
        for cand_item in candidate_items:
            cand_lower = cand_item.lower()
            if req_lower in cand_lower or cand_lower in req_lower:
                return True
            req_words = set(req_lower.split())
            cand_words = set(cand_lower.split())
            if req_words & cand_words:
                return True
        return False
    
    all_requirements = []
    for req in job_analysis.requirements.education:
        all_requirements.append((req.name, req.status))
    for req in job_analysis.requirements.technical_skills:
        all_requirements.append((req.name, req.status))
    for req in job_analysis.requirements.experience:
        all_requirements.append((req.name, req.status))
    for req in job_analysis.requirements.technologies:
        all_requirements.append((req.name, req.status))
    for req in job_analysis.requirements.skills:
        all_requirements.append((req.name, req.status))
    for req in job_analysis.requirements.languages:
        all_requirements.append((req.name, req.status))
    
    all_candidate_items = (
        candidate_profile.education + candidate_profile.technical_skills +
        candidate_profile.technologies + candidate_profile.skills +
        candidate_profile.languages + candidate_profile.experience
    )
    
    required_count = 0
    preferred_count = 0
    matched_count = 0
    
    for req_name, req_status in all_requirements:
        is_matched = check_match(req_name, all_candidate_items)
        if is_matched:
            matched.append(req_name)
            matched_count += 1
        else:
            if req_status == "required":
                missing_required.append(req_name)
                required_count += 1
            elif req_status == "preferred":
                missing_preferred.append(req_name)
                preferred_count += 1
    
    total_requirements = len(all_requirements)
    if total_requirements == 0:
        overall_score = 50
    else:
        score = (matched_count * 10) - (required_count * 5) - (preferred_count * 2)
        overall_score = max(0, min(100, 50 + score))
    
    if overall_score >= 80:
        match_level = "high"
    elif overall_score >= 50:
        match_level = "medium"
    elif overall_score >= 20:
        match_level = "low"
    else:
        match_level = "no_match"
    
    notes = []
    if matched:
        notes.append(f"Matched: {', '.join(matched[:5])}")
    if missing_required:
        notes.append(f"Missing required: {', '.join(missing_required[:3])}")
    if missing_preferred:
        notes.append(f"Missing preferred: {', '.join(missing_preferred[:3])}")
    
    score_object =  MatchScore(
        overall_score=overall_score,
        job_id= job_id,
        match_level=match_level,
        matched_requirements=matched,
        missing_required=missing_required,
        missing_preferred=missing_preferred,
        analysis_notes=" | ".join(notes) if notes else "No analysis available"
    )
    return score_object

def analyze_and_score_job(job: Job, extracted_requirements) -> MatchScore:
    # Complete workflow: analyze job with LLM and calculate match score.
    # Convert dict to Job_validation model if needed (e.g., when loaded from JSON string in DB)
    if isinstance(extracted_requirements, dict):
        job_analysis = Job_validation.model_validate(extracted_requirements)
    else:
        job_analysis = extracted_requirements
    match_score = calculate_match_score(job_analysis, candidate, job.job_id)
    return match_score


def get_job_details(job):
    response = client.interactions.create(
        model = "gemini-3.5-flash-lite",
        system_instruction="""
            Analyze the job description.
            Extract the requirements and classify each requirement as:
            - required: explicitly required by the job
            - preferred: explicitly described as preferred, desirable, a plus, or advantageous
            - unknown: the job mentions the concept but does not make its importance clear
            Do not invent candidate experience.
            The category describes the type of job, for example: SAP Finance / Data Analytics.
            "category" must NOT contain required, preferred, or unknown.
        """,
        input=[
            {
                "type": "text",
                "text": job.description
            }
        ],
        response_format=Job_validation.model_json_schema(),
        stream = False
    )
    if response.output_text is None:
        raise ValueError("Gemini returned no text output")
    return response.output_text
