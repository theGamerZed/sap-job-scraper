from ollama import chat
from pydantic import BaseModel,Field
from typing import Literal
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

job = Job(
    title="SAP Finance / Data Analytics Working Student",
    job_id=123456,
    location="Walldorf, Germany",
    description="""
    We are looking for a working student to support our Finance and
    Data Analytics team.

    You are currently studying Computer Science, Business Informatics,
    Business Administration, or a related field.

    You should have an interest in SAP ERP systems and data analytics.
    Experience with SAP is preferred.

    You will support planning, organization and agile project work.
    Knowledge of DevOps and software lifecycle processes is a plus.

    Strong analytical thinking, problem solving and teamwork skills
    are expected.

    Fluency in English is required. German is a plus.
    """
)

# response: ChatResponse = chat(
#   model='qwen3:4b',
#   messages=[
#     {
#       'role': 'user',
#       'content': 'Why is the sky blue?',
#     },
#   ],
# )
# response = chat(
#     model="qwen3.5:0.8b",
#     messages=[
#         {
#             "role": "system",
#             "content": """
#             Analyze the job description and extract its requirements.

#             Distinguish between required and preferred requirements where
#             possible.

#             Do not invent information that is not present in the job description.
#             """
#         },
#         {
#             "role": "user",
#             "content": job.description
#         }
#     ],
#     format=Job_validation.model_json_schema()
# )
# #print(response['message']['content'])
# # or access fields directly from the response object


response = chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "system",
            "content": """
            Analyze the job description.

            Extract the requirements and classify each requirement as:

            - required: explicitly required by the job
            - preferred: explicitly described as preferred, desirable,
              a plus, or advantageous
            - unknown: the job mentions the concept but does not make
              its importance clear

            Do not invent candidate experience.

            The category describes the type of job, for example:
            SAP Finance / Data Analytics.

            "category" must NOT contain required, preferred, or unknown.
            """
        },
        {
            "role": "user",
            "content": job.description
        }
    ],
    format=Job_validation.model_json_schema()
)
print(response.message.content)
