from ollama import chat
from ollama import ChatResponse
from pydantic import BaseModel 
from typing import Literal
class Job(BaseModel):
    title: str
    job_id: int 
    location: str
    description: str

class Requirements(BaseModel):
  education: str
  technical_skills: list[str]
  experience: list[str] | None = None
  technologies: list[str]
  skills: list[str]
  languages: list[str]
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
response = chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "system",
            "content": """
            Analyze the job description and extract its requirements.

            Distinguish between required and preferred requirements where
            possible.

            Do not invent information that is not present in the job description.
            """
        },
        {
            "role": "user",
            "content": job.description
        }
    ],
    format=Job_validation.model_json_schema()
)
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)






# {
#     "type": "object", 
#     "properties": { 
#         "name": {
#             "type": "string"
#         },
#         "capital": {
#             "type": "string"
#         }, 
#         "languages": {
#             "type": "array",
#             "items": {"type": "string"} 
#         } 
#     }, 
#     "required": ["name", "capital", "languages"] 
# } 