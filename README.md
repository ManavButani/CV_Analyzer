# CV Analyzer - Resume Screening Orchestrator

AI-powered Resume Screening System that automatically evaluates, ranks, and explains candidate suitability for job descriptions using explainable AI-driven analysis.

## Overview

The CV Analyzer is an intelligent resume screening system that:

- Analyzes job descriptions to extract requirements
- Parses and structures resume data
- Matches skills with intelligent synonym handling
- Evaluates experience relevance and role alignment
- Scores and ranks candidates with transparent reasoning
- Provides detailed explanations for each ranking decision

## Base URL

**Local Development:** `http://localhost:8000`  
**API Documentation:** `http://localhost:8000/scrapper_application/docs`

## Authentication

All endpoints (except registration and login) require JWT authentication. Tokens expire after 30 minutes.

---

## API Endpoints

### 1. User Management

#### Register New User

**Endpoint:** `POST /scrapper_application/user/register/`

**Request Body:**

```json
{
  "username": "string",
  "password": "string",
  "email": "string (optional)",
  "full_name": "string (optional)"
}
```

**Response:**

```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false
}
```

#### Get Current User

**Endpoint:** `GET /scrapper_application/user/me/`  
**Authentication:** Required

**Response:**

```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false
}
```

---

### 2. Authentication

#### Login

**Endpoint:** `POST /scrapper_application/auth/login/`

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "jwt_token_string",
  "token_type": "bearer"
}
```

**Note:** Token is valid for 30 minutes. Include it in subsequent requests as:

```
Authorization: Bearer <access_token>
```

---

### 3. LLM Provider Management

#### Configure LLM Provider

**Endpoint:** `POST /scrapper_application/llm_provider/configure/`  
**Authentication:** Required

**Request Body:**

```json
{
  "provider_name": "openai | gemini | grok",
  "api_key": "string",
  "model_name": "string (optional, e.g., 'gpt-4o', 'gemini-2.5-flash')",
  "is_active": true
}
```

**Response:**

```json
{
  "id": 1,
  "provider_name": "openai",
  "model_name": "gpt-4o",
  "is_active": true
}
```

#### Activate LLM Provider

**Endpoint:** `POST /scrapper_application/llm_provider/activate/{provider_name}/`  
**Authentication:** Required

**Response:**

```json
{
  "id": 1,
  "provider_name": "openai",
  "model_name": "gpt-4o",
  "is_active": true
}
```

#### Get Provider Status

**Endpoint:** `GET /scrapper_application/llm_provider/status/`  
**Authentication:** Required

**Response:**

```json
[
  {
    "provider_name": "openai",
    "model_name": "gpt-4o",
    "is_active": true
  },
  {
    "provider_name": "gemini",
    "model_name": "gemini-2.5-flash",
    "is_active": false
  }
]
```

---

### 4. Resume Screening

#### Screen Resumes (JSON Input)

**Endpoint:** `POST /scrapper_application/resume_screening/screen/`  
**Authentication:** Required

**Request Body:**

```json
{
  "jd": {
    "jd_text": "Job description text (optional if jd_file provided)",
    "jd_file": "base64_encoded_file_content (optional if jd_text provided)",
    "file_format": "pdf | docx | txt"
  },
  "resumes": [
    {
      "resume_text": "Resume text content (optional if resume_file provided)",
      "resume_file": "base64_encoded_file_content (optional if resume_text provided)",
      "file_format": "pdf | docx | txt",
      "candidate_name": "John Doe (optional)"
    }
  ],
  "scoring_weights": {
    "skills_match": 0.4,
    "relevant_experience": 0.35,
    "role_alignment": 0.15,
    "education_certifications": 0.1
  }
}
```

**Response:**

```json
{
  "ranked_candidates": [
    {
      "candidate_name": "John Doe",
      "rank": 1,
      "overall_score": 85.5,
      "score_breakdown": {
        "skills_score": 90.0,
        "experience_score": 85.0,
        "role_alignment_score": 80.0,
        "education_score": 100.0,
        "weighted_total_score": 85.5,
        "scoring_explanation": "Skills: 90.0% (weight: 40%), Experience: 85.0% (weight: 35%)..."
      },
      "explanation": {
        "rank_position": 1,
        "overall_match_score": 85.5,
        "strengths": [
          "Strong match with mandatory skills",
          "Relevant domain experience"
        ],
        "gaps": [
          "Missing preferred skill: Kubernetes"
        ],
        "missing_requirements": [],
        "risk_flags": [],
        "reasoning": "Candidate demonstrates strong alignment..."
      },
      "structured_resume": {
        "candidate_name": "John Doe",
        "skills": ["Python", "FastAPI", "Docker"],
        "experience": [...],
        "total_years_experience": 5.0,
        "education": [...],
        "certifications": [...]
      }
    }
  ],
  "summary": {
    "top_3_candidates": [
      {
        "name": "John Doe",
        "score": 85.5,
        "rank": 1
      }
    ],
    "common_gaps_observed": [
      "Missing Kubernetes experience",
      "Limited cloud certifications"
    ],
    "hiring_risks": [
      "Talent scarcity in specific domain",
      "High competition for top candidates"
    ],
    "overall_statistics": {
      "total_candidates": 5,
      "average_score": 72.3,
      "max_score": 85.5,
      "min_score": 45.2
    }
  },
  "scoring_weights_used": {
    "skills_match": 0.40,
    "relevant_experience": 0.35,
    "role_alignment": 0.15,
    "education_certifications": 0.10
  },
  "processing_metadata": {
    "request_id": "uuid-string",
    "total_resumes_processed": 5,
    "total_candidates_ranked": 5,
    "model_reasoning_steps": 12
  }
}
```

#### Screen Resumes (File Upload)

**Endpoint:** `POST /scrapper_application/resume_screening/screen/files/`  
**Authentication:** Required  
**Content-Type:** `multipart/form-data`

**Form Data:**

- `jd_file`: File (PDF/DOCX/TXT) - Job Description
- `resume_files`: Files[] (PDF/DOCX/TXT) - Multiple resumes
- `model`: String (optional) - Model name override

**Response:** Same as `/screen/` endpoint

---

### 5. Screening History

#### Get Screening Request by ID

**Endpoint:** `GET /scrapper_application/screening_history/history/{request_id}`  
**Authentication:** Required

**Response:**

```json
{
  "request_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:00Z",
  "model_provider": "openai",
  "model_name": "gpt-4o",
  "jd_file_path": "uploads/jd/xxx.pdf",
  "resume_files_paths": ["uploads/resumes/xxx.pdf"],
  "resume_count": 5,
  "total_resumes_processed": 5,
  "total_candidates_ranked": 5,
  "processing_status": "completed",
  "reasoning_json": [...],
  "output_json": {...},
  "intermediate_outputs": {...}
}
```

#### List All Screening Requests

**Endpoint:** `GET /scrapper_application/screening_history/history/?limit=100&offset=0`  
**Authentication:** Required

**Query Parameters:**

- `limit`: Number of records (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

**Response:**

```json
[
  {
    "request_id": "uuid-string",
    "timestamp": "2024-01-15T10:30:00Z",
    "model_provider": "openai",
    "model_name": "gpt-4o",
    "resume_count": 5,
    "total_resumes_processed": 5,
    "total_candidates_ranked": 5,
    "processing_status": "completed"
  }
]
```

---

## How It Works

### System Architecture

The system uses an **Orchestrator Agent** that coordinates multiple specialized AI agents:

1. **JD Analyzer Agent**: Extracts structured information from job descriptions

   - Mandatory and preferred skills
   - Experience requirements
   - Role seniority
   - Education/certification requirements

2. **Resume Parser Agent**: Converts resumes into structured data

   - Skills extraction
   - Experience parsing (roles, companies, years)
   - Education and certifications
   - Projects and achievements

3. **Skill Matching Agent**: Matches resume skills against JD requirements

   - Handles synonyms (e.g., "PyTorch" = "Deep Learning")
   - Partial matches
   - Calculates skill match score (0-100)

4. **Experience Evaluation Agent**: Assesses experience relevance

   - Domain relevance scoring
   - Role alignment assessment
   - Overqualification detection
   - Irrelevant experience penalty

5. **Scoring & Ranking Agent**: Combines all signals into final scores
   - Weighted scoring (configurable weights)
   - Tie resolution logic
   - Missing data handling
   - Generates explanations

### Scoring Logic

**Default Weight Distribution:**

- Skills Match: 40%
- Relevant Experience: 35%
- Role Alignment: 15%
- Education/Certifications: 10%

**Tie Resolution:**
When candidates have the same overall score, ranking is determined by:

1. Skills match score (higher = better)
2. Experience score (higher = better)
3. Role alignment score (higher = better)
4. Education score (higher = better)

**Missing Data Handling:**

- Missing skills: Score = 0 for skill matching
- Missing experience: Experience score = 0
- Missing education (when required): Education score = 0
- Missing optional fields: No penalty

### Processing Flow

1. **JD Analysis**: Parse and structure the job description
2. **Resume Analysis**: For each resume:
   - Parse resume content
   - Match skills against JD
   - Evaluate experience
   - Calculate scores
   - Generate explanations
3. **Ranking**: Sort candidates by weighted total score
4. **Summary Generation**: Create final summary with top candidates and insights

### Model-Driven Decisions

- All decisions are made by AI models (no hard-coded logic)
- Rankings are explainable with detailed reasoning
- Intermediate outputs are tracked for transparency
- Model reasoning is logged and stored

---

## File Formats Supported

- **PDF**: `.pdf` files
- **DOCX**: Microsoft Word documents
- **TXT**: Plain text files

---

## Error Handling

The system provides detailed error messages with:

- HTTP status codes
- Error descriptions
- Traceback information (for debugging)
- Suggestions for resolution

**Common Error Codes:**

- `400`: Bad Request (invalid input, missing data)
- `401`: Unauthorized (invalid or expired token)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error (system error)

---

## Example Usage

### Python Example

```python
import requests
import base64

# 1. Login
login_response = requests.post(
    "http://localhost:8000/scrapper_application/auth/login/",
    json={"username": "your_username", "password": "your_password"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Configure LLM Provider
requests.post(
    "http://localhost:8000/scrapper_application/llm_provider/configure/",
    headers=headers,
    json={
        "provider_name": "openai",
        "api_key": "your-api-key",
        "model_name": "gpt-4o",
        "is_active": True
    }
)

# 3. Screen Resumes
with open("job_description.pdf", "rb") as f:
    jd_content = base64.b64encode(f.read()).decode()

resumes = []
for resume_file in ["resume1.pdf", "resume2.pdf"]:
    with open(resume_file, "rb") as f:
        resumes.append({
            "resume_file": base64.b64encode(f.read()).decode(),
            "file_format": "pdf"
        })

response = requests.post(
    "http://localhost:8000/scrapper_application/resume_screening/screen/",
    headers=headers,
    json={
        "jd": {
            "jd_file": jd_content,
            "file_format": "pdf"
        },
        "resumes": resumes,
        "scoring_weights": {
            "skills_match": 0.40,
            "relevant_experience": 0.35,
            "role_alignment": 0.15,
            "education_certifications": 0.10
        }
    }
)

result = response.json()
print(f"Top candidate: {result['ranked_candidates'][0]['candidate_name']}")
print(f"Score: {result['ranked_candidates'][0]['overall_score']}")
```

---

## Features

✅ **Multi-Provider LLM Support**: Switch between OpenAI, Gemini, or Grok  
✅ **Explainable Rankings**: Detailed reasoning for each candidate  
✅ **Intelligent Skill Matching**: Handles synonyms and partial matches  
✅ **Experience Evaluation**: Domain relevance and role alignment assessment  
✅ **Configurable Scoring**: Customize weight distribution  
✅ **Request History**: Track all screening requests with reasoning  
✅ **File Storage**: Automatic storage of input files  
✅ **Missing Data Handling**: Robust handling of incomplete resumes  
✅ **Tie Resolution**: Deterministic ranking for equal scores

---

## Local Development

### Prerequisites

- Python 3.11+
- SQLite (or PostgreSQL for production)
- LLM API key (OpenAI, Gemini, or Grok)

### Setup

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure Environment**
   Create a `.env` file:

```
OPENAI_API_KEY=your_key_here
JWT_SECRET=your_jwt_secret_here
```

3. **Initialize Database**
   The database tables are created automatically on first run.

4. **Run Application**

```bash
uvicorn main:app --reload
```

5. **Access API Documentation**
   Open `http://localhost:8000/scrapper_application/docs`

---

## Notes

- Tokens expire after 30 minutes - re-authenticate as needed
- File uploads are stored in the `uploads/` directory
- All screening requests are stored in the database with full reasoning
- The system uses a single LLM call per resume for efficiency
- Model reasoning is captured and stored for explainability
