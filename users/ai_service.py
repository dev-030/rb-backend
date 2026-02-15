"""
AI-powered career analysis service for resume evaluation and career recommendations.
"""
import json
import re
import requests
import fitz  # PyMuPDF
import docx  # python-docx
from io import BytesIO
from typing import Dict, List, Any
from django.conf import settings
from openai import OpenAI


class PDFParser:
    """Production-grade PDF text extraction service using PyMuPDF."""
    
    @staticmethod
    def download_and_extract_text(url: str, max_pages: int = 5) -> str:
        """
        Download PDF from Cloudinary and extract text with advanced cleaning.
        
        Industry best practices:
        - Uses PyMuPDF (fitz) - fastest and most accurate Python PDF library
        - Preserves layout with proper spacing
        - Handles multi-column text
        - Cleans control characters and extra whitespace
        - Limits pages for performance
        
        Args:
            url: Cloudinary URL of the PDF resume
            max_pages: Maximum pages to process (default 5 for resumes)
            
        Returns:
            Clean, formatted text content from PDF
            
        Raises:
            Exception: If download or parsing fails
        """
        try:
            # Download PDF from Cloudinary with timeout
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Open PDF from bytes stream
            pdf_document = fitz.open(stream=response.content, filetype="pdf")
            
            # Extract text from pages
            text_content = []
            pages_to_process = min(pdf_document.page_count, max_pages)
            
            for page_num in range(pages_to_process):
                page = pdf_document[page_num]
                
                # Extract text with layout preservation
                # "text" mode preserves layout better than "blocks"
                page_text = page.get_text("text")
                
                if page_text.strip():
                    text_content.append(page_text)
            
            pdf_document.close()
            
            # Combine all pages
            full_text = "\n\n".join(text_content)
            
            # Advanced text cleaning
            cleaned_text = PDFParser._clean_text(full_text)
            
            return cleaned_text
            
        except requests.RequestException as e:
            raise Exception(f"Failed to download PDF from Cloudinary: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean extracted PDF text with production-grade processing.
        
        Handles:
        - Control characters
        - Excessive whitespace
        - Broken lines
        - Special characters
        """
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 newlines
        
        # Fix common PDF extraction issues
        text = text.replace('\u2022', '•')  # Bullet points
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '--')  # Em dash
        text = text.replace('\u2019', "'")  # Smart quote
        text = text.replace('\u201c', '"')  # Smart quote
        text = text.replace('\u201d', '"')  # Smart quote
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()


class DocxParser:
    """Production-grade DOCX text extraction service using python-docx."""
    
    @staticmethod
    def download_and_extract_text(url: str) -> str:
        """
        Download DOCX from Cloudinary and extract text.
        
        Args:
            url: Cloudinary URL of the DOCX resume
            
        Returns:
            Clean, formatted text content from DOCX
            
        Raises:
            Exception: If download or parsing fails
        """
        try:
            # Download DOCX from Cloudinary with timeout
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Open DOCX from bytes stream
            doc_file = BytesIO(response.content)
            document = docx.Document(doc_file)
            
            # Extract text from paragraphs
            text_content = []
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Combine paragraphs
            full_text = "\n\n".join(text_content)
            
            # Advanced text cleaning (reuse PDFParser logic)
            cleaned_text = PDFParser._clean_text(full_text)
            
            return cleaned_text
            
        except requests.RequestException as e:
            raise Exception(f"Failed to download DOCX from Cloudinary: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
class CareerAnalyzer:
    """AI-powered career analysis using OpenAI GPT-4o with vision."""
    
    def __init__(self):
        """Initialize OpenAI client with API key from settings."""
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in settings")
        self.client = OpenAI(api_key=api_key)
        # Use gpt-4o by default (cheaper and supports vision)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')
        
        # Fetch available categories from database (with full details)
        self.categories = self._get_categories()
    
    def _get_categories(self):
        """Fetch all active categories with ID, name, and description."""
        try:
            from users.models import Category
            categories = Category.objects.filter(is_active=True).values('id', 'name', 'slug', 'description')
            return list(categories) if categories else []
        except Exception:
            # Fallback to default categories if database query fails
            return [
                {'id': None, 'name': 'Healthcare', 'slug': 'healthcare', 'description': 'Healthcare and medical services'},
                {'id': None, 'name': 'Technology', 'slug': 'technology', 'description': 'IT, software, and technology services'},
                {'id': None, 'name': 'Construction', 'slug': 'construction', 'description': 'Construction and building trades'},
                {'id': None, 'name': 'Retail', 'slug': 'retail', 'description': 'Retail sales and customer service'},
                {'id': None, 'name': 'Hospitality', 'slug': 'hospitality', 'description': 'Hotels, restaurants, and tourism'},
                {'id': None, 'name': 'Manufacturing', 'slug': 'manufacturing', 'description': 'Manufacturing and production'},
                {'id': None, 'name': 'Education', 'slug': 'education', 'description': 'Education and training'},
                {'id': None, 'name': 'Finance', 'slug': 'finance', 'description': 'Finance, banking, and accounting'},
                {'id': None, 'name': 'Other', 'slug': 'other', 'description': 'Other categories'}
            ]
    
    def analyze_career_path(
        self,
        quiz_data: Dict[str, str],
        work_history: List[Dict[str, Any]],
        resume_text: str
    ) -> Dict[str, Any]:
        """
        Analyze user data and resume text to provide career recommendations.
        
        Args:
            quiz_data: User's quiz responses (interests, work environment, etc.)
            work_history: List of work history entries
            resume_text: Extracted and cleaned text from PDF resume
            
        Returns:
            Structured career analysis with resume score and recommendations
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(quiz_data, work_history, resume_text)
        
        try:
            # Call OpenAI API with text-only (faster and cheaper than vision)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert career counselor and resume analyst. "
                            "Your primary goal is to provide ACCURATE and HELPFUL analysis. "
                            "When evaluating resumes, be thorough in reading ALL content before judging completeness. "
                            "Do NOT mark sections as incomplete unless they are truly missing or severely lacking. "
                            "If a section has reasonable content, mark it as complete. "
                            "Provide specific, actionable suggestions based on what you actually observe in the resume. "
                            "Return ONLY a valid JSON response with resume analysis and career recommendations. "
                            "Do not include any explanatory text outside the JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and structure the response
            return self._structure_response(result)
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def analyze_career_path_from_image(
        self,
        quiz_data: Dict[str, str],
        work_history: List[Dict[str, Any]],
        image_url: str
    ) -> Dict[str, Any]:
        """
        Analyze user data and resume IMAGE to provide career recommendations.
        Uses GPT-4o Vision to read resume directly from image.
        
        Args:
            quiz_data: User's quiz responses (interests, work environment, etc.)
            work_history: List of work history entries
            image_url: URL to the resume image (JPG, PNG, etc.)
            
        Returns:
            Structured career analysis with resume score and recommendations
        """
        # Build the analysis prompt (same as text version)
        prompt = self._build_analysis_prompt(quiz_data, work_history, "")
        
        # Modify prompt to work with vision
        vision_prompt = prompt.replace(
            "**Resume Text:**\n",
            "**Resume Image:**\nPlease carefully read ALL text visible in the resume image provided. "
            "Extract and analyze all information including personal details, education, work experience, and skills.\n\n"
        )
        
        try:
            # Call OpenAI API with vision (gpt-4o supports images)
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Must use gpt-4o or gpt-4o-mini for vision
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert career counselor and resume analyst. "
                            "Your primary goal is to provide ACCURATE and HELPFUL analysis. "
                            "When evaluating resumes, be thorough in reading ALL content visible in the image before judging completeness. "
                            "Do NOT mark sections as incomplete unless they are truly missing or severely lacking. "
                            "If a section has reasonable content, mark it as complete. "
                            "Provide specific, actionable suggestions based on what you actually observe in the resume. "
                            "Return ONLY a valid JSON response with resume analysis and career recommendations. "
                            "Do not include any explanatory text outside the JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": vision_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "high"  # High detail for better text recognition
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and structure the response
            return self._structure_response(result)
            
        except Exception as e:
            raise Exception(f"OpenAI Vision API error: {str(e)}")
    
    def _build_analysis_prompt(
        self,
        quiz_data: Dict[str, str],
        work_history: List[Dict[str, Any]],
        resume_text: str
    ) -> str:
        """Build the analysis prompt for OpenAI with resume text."""
        work_history_summary = "\n".join([
            f"- {item.get('job_title', 'N/A')} at {item.get('company_name', 'N/A')} "
            f"({item.get('start_date', 'N/A')} to {item.get('end_date', 'Present')}): "
            f"{item.get('responsibilities', 'N/A')}"
            for item in work_history
        ])
        
        has_work_history = len(work_history) > 0
        
        # Limit resume text to avoid token limits (keep first 3000 chars)
        resume_preview = resume_text[:3000] if len(resume_text) > 3000 else resume_text
        
        # Format categories for AI with full details
        categories_list = "\n".join([
            f"- ID: {cat.get('id')}, Name: {cat['name']}, Description: {cat.get('description', 'N/A')}"
            for cat in self.categories
        ])
        
        prompt = f"""
Analyze the resume text provided along with the following user data and provide career recommendations:

**Quiz Responses:**
- Interests: {quiz_data.get('interests', 'N/A')}
- Preferred Work Environment: {quiz_data.get('work_environment', 'N/A')}
- Training Flexibility: {quiz_data.get('training_flexibility', 'N/A')}
- Key Strengths: {quiz_data.get('strengths', 'N/A')}
- Job Priorities: {quiz_data.get('job_priorities', 'N/A')}
- Location Preference: {quiz_data.get('location', 'N/A')}

**Work History (User-Provided - Already Verified):**
{work_history_summary if has_work_history else "No work history provided"}

IMPORTANT: The work history above is user-provided and verified. When assessing resume completeness:
- If work history is provided above, mark "work_experience" as "complete"
- The resume text may supplement this information but should not override it

**Resume Text:**
{resume_preview}

**AVAILABLE CAREER CATEGORIES (From Database):**
You MUST recommend from ONLY these categories. Use the EXACT category data provided:

{categories_list}

CRITICAL INSTRUCTIONS FOR CAREER RECOMMENDATIONS:
1. DO NOT create custom job titles like "Software Developer" or "IT Manager"
2. You MUST use the exact category names from the list above
3. For each recommendation, use:
   - category_id: The exact ID from the list
   - title: The exact category NAME from the list (e.g., "Technology", "Healthcare")
   - description: The exact category DESCRIPTION from the list, OR if empty, create a brief description of careers in that category
4. Choose 1 primary and 2 alternative categories based on user's profile

**Instructions:**
CRITICAL: BE ACCURATE! This resume will be evaluated for completeness. Do NOT mark sections as incomplete unless they are truly missing or severely lacking content.

COMPLETENESS EVALUATION CRITERIA:

1. **Personal Info** - Mark as "complete" if the resume contains AT LEAST THREE of:
   - Full name
   - Phone number OR email address
   - LinkedIn, GitHub, or portfolio URL
   - Location/Address
   
2. **Education** - Mark as "complete" if it has AT LEAST ONE of:
   - University/College name AND degree/major
   - High school with graduation year
   - Any formal educational institution listed
   
3. **Work Experience** - Mark as "complete" if it has AT LEAST ONE of:
   - Job title AND company name
   - Internship with company/organization
   - Project work with dates
   - Volunteer experience
   
4. **Skills** - Mark as "complete" if it lists AT LEAST THREE items that could be:
   - Programming languages
   - Technical tools
   - Soft skills
   - Frameworks/technologies
   - Languages spoken

COMPLETENESS SCORE GUIDELINES:
- 90-100: Excellent resume with all sections complete and well-detailed
- 70-89: Good resume with all major sections present
- 50-69: Adequate resume with some sections needing improvement
- 30-49: Basic resume with multiple sections incomplete
- 0-29: Very incomplete resume missing most sections

BE GENEROUS: If a resume has reasonable content in a section, mark it as "complete". Only mark as "incomplete" if the section is truly missing or has minimal/placeholder content.

Provide a JSON response with the following structure:

{{
  "resume_analysis": {{
    "completeness_score": <integer 0-100>,
    "section_status": {{
      "personal_info": "<complete|incomplete>",
      "education": "<complete|incomplete>",
      "work_experience": "<complete|incomplete>",
      "skills": "<complete|incomplete>"
    }},
    "suggestions": [
      "<actionable suggestion 1>",
      "<actionable suggestion 2>",
      "<actionable suggestion 3>"
    ]
  }},
  "career_recommendations": [
    {{
      "category_id": "<exact ID from category list>",
      "title": "<exact category NAME from list, e.g., 'Technology', 'Healthcare'>",
      "description": "<exact category DESCRIPTION from list, or brief description of careers in this category>",
      "training_duration": "<e.g., '3-6 months', 'Less than 3 months'>",
      "match_type": "primary"
    }},
    {{
      "category_id": "<exact ID from category list>",
      "title": "<exact category NAME>",
      "description": "<exact category DESCRIPTION or brief description>",
      "training_duration": "<duration>",
      "match_type": "alternative"
    }}
  ]
}}

**Guidelines:**
1. ACCURATELY assess completeness based on what's ACTUALLY in the resume text above
2. Only provide suggestions for sections that are truly incomplete or could be meaningfully improved
3. Recommend 3-5 career paths based on the user's actual skills and experience shown in the resume
4. Mark the top match as "primary" and others as "alternative"
5. Training duration should align with their stated training flexibility
6. Consider their job priorities (salary, work-life balance, etc.) in recommendations
"""
        return prompt
    
    def _structure_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and structure the AI response to ensure it matches expected format.
        
        Args:
            ai_response: Raw response from OpenAI
            
        Returns:
            Validated and structured response
        """
        # Ensure required keys exist
        if 'resume_analysis' not in ai_response:
            ai_response['resume_analysis'] = {
                'completeness_score': 50,
                'section_status': {
                    'personal_info': 'incomplete',
                    'education': 'incomplete',
                    'work_experience': 'incomplete',
                    'skills': 'incomplete'
                },
                'suggestions': ['Complete all resume sections for better analysis']
            }
        
        if 'career_recommendations' not in ai_response:
            ai_response['career_recommendations'] = []
        
        # Ensure completeness_score is an integer
        resume_analysis = ai_response['resume_analysis']
        if 'completeness_score' in resume_analysis:
            resume_analysis['completeness_score'] = int(resume_analysis['completeness_score'])
        
        # Ensure at least one primary recommendation exists
        has_primary = any(
            rec.get('match_type') == 'primary'
            for rec in ai_response['career_recommendations']
        )
        
        if not has_primary and ai_response['career_recommendations']:
            ai_response['career_recommendations'][0]['match_type'] = 'primary'
        
        return ai_response


# Main service interface
def analyze_career_data(
    quiz_data,
    work_history,
    pdf_url
):
    """
    Main function to analyze career data and provide recommendations.
    
    Supports both PDF files and images (JPG, PNG) of resumes.
    
    Args:
        quiz_data: User's quiz responses
        work_history: User's work history
        pdf_url: Cloudinary URL of the resume (PDF or image)
        
    Returns:
        Structured analysis with resume score and career recommendations
        
    Raises:
        Exception: If any step of the analysis fails
    """
    # Check if the URL is an image or PDF
    url_lower = pdf_url.lower()
    is_image = url_lower.endswith(('.jpg', '.jpeg', '.png', '.webp'))
    
    analyzer = CareerAnalyzer()
    
    if is_image:
        # Use GPT-4o Vision to analyze image directly
        print(f"📸 Detected image resume: {pdf_url}")
        analysis_result = analyzer.analyze_career_path_from_image(quiz_data, work_history, pdf_url)
    elif url_lower.endswith('.docx'):
        # Extract text from DOCX, then analyze
        print(f"📝 Detected DOCX resume: {pdf_url}")
        docx_parser = DocxParser()
        resume_text = docx_parser.download_and_extract_text(pdf_url)
        analysis_result = analyzer.analyze_career_path(quiz_data, work_history, resume_text)
    else:
        # Extract text from PDF first, then analyze
        print(f"📄 Detected PDF resume: {pdf_url}")
        pdf_parser = PDFParser()
        resume_text = pdf_parser.download_and_extract_text(pdf_url)
        analysis_result = analyzer.analyze_career_path(quiz_data, work_history, resume_text)
    
    return analysis_result




def _validate_quiz_data(quiz_data: Dict[str, str]) -> None:
    """
    Validate quiz_data has required fields.
    
    Raises:
        ValueError: If quiz_data is invalid
    """
    required_fields = ['interests', 'work_environment', 'training_flexibility', 
                      'strengths', 'job_priorities', 'location']
    
    if not quiz_data:
        raise ValueError("quiz_data is required")
    
    for field in required_fields:
        if field not in quiz_data:
            raise ValueError(f"Missing required field: {field}")
        
        # Check that values aren't empty
        if not quiz_data[field] or not str(quiz_data[field]).strip():
            raise ValueError(f"Field '{field}' cannot be empty")


# New service for job and training recommendations
def recommend_jobs_and_trainings(quiz_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Recommend jobs and training programs based on quiz data.
    
    Args:
        quiz_data: User's quiz responses (interests, work environment, etc.)
        
    Returns:
        Dictionary with recommended_jobs and recommended_trainings lists
        
    Raises:
        ValueError: If quiz_data is invalid
        Exception: If AI analysis fails
    """
    # Step 0: Validate input data
    _validate_quiz_data(quiz_data)
    
    # Step 1: Fetch limited active jobs from database (only top 50)
    jobs_data = _get_active_jobs(limit=50)
    
    # Step 2: Fetch limited active training programs (only top 30)
    trainings_data = _get_active_trainings(limit=30)
    
    # Step 3: Handle empty data gracefully
    if not jobs_data and not trainings_data:
        return {
            'recommended_jobs': [],
            'recommended_trainings': []
        }
    
    # Step 4: Use AI to analyze and recommend (AI returns minimal data with IDs)
    recommendations = _analyze_with_ai(quiz_data, jobs_data, trainings_data)
    
    # Step 5: Enrich AI response with full job/training data
    enriched_recommendations = _enrich_recommendations(recommendations, jobs_data, trainings_data)
    
    return enriched_recommendations


def _enrich_recommendations(
    ai_response: Dict[str, Any],
    jobs_data: List[Dict[str, Any]],
    trainings_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enrich AI response with full job and training data.
    AI returns minimal data with IDs and match_reason.
    We look up the full data from our original lists.
    """
    # Create lookup dictionaries for fast access
    jobs_lookup = {job['id']: job for job in jobs_data}
    trainings_lookup = {training['id']: training for training in trainings_data}
    
    enriched_jobs = []
    for ai_job in ai_response.get('recommended_jobs', []):
        job_id = ai_job.get('id')
        if job_id and job_id in jobs_lookup:
            # Get full job data from our original list
            full_job = jobs_lookup[job_id].copy()
            # Add AI's match_reason
            full_job['match_reason'] = ai_job.get('match_reason', 'Good match for your profile')
            enriched_jobs.append(full_job)
    
    enriched_trainings = []
    for ai_training in ai_response.get('recommended_trainings', []):
        training_id = ai_training.get('id')
        if training_id and training_id in trainings_lookup:
            # Get full training data from our original list
            full_training = trainings_lookup[training_id].copy()
            # Add AI's match_reason
            full_training['match_reason'] = ai_training.get('match_reason', 'Good match for your profile')
            enriched_trainings.append(full_training)
    
    return {
        'recommended_jobs': enriched_jobs,
        'recommended_trainings': enriched_trainings
    }



def _get_active_jobs(limit=50) -> List[Dict[str, Any]]:
    """Fetch recent active jobs with essential details only (optimized for AI)."""
    try:
        from users.models import Job
        # Limit to most recent jobs and only fetch needed fields
        jobs = Job.objects.filter(
            status='active'
        ).select_related(
            'employer', 'category'
        ).order_by('-created_at')[:limit]
        
        jobs_list = []
        for job in jobs:
            jobs_list.append({
                'id': str(job.id),
                'title': job.title,
                'company_name': job.employer.company_name,
                'description': job.description[:150],  # Truncate for AI efficiency
                'location': job.location,
                'employment_type': job.get_employment_type_display(),
                'salary_min': float(job.salary_min) if job.salary_min else None,
                'salary_max': float(job.salary_max) if job.salary_max else None,
                'skills_required': job.skills_required[:5] if job.skills_required else [],  # Limit skills
                'is_remote': job.is_remote,
                'category': job.category.name if job.category else None
            })
        
        return jobs_list
    except Exception as e:
        # Return empty list instead of crashing
        import logging
        logging.error(f"Failed to fetch jobs: {str(e)}")
        return []


def _get_active_trainings(limit=30) -> List[Dict[str, Any]]:
    """Fetch recent active training programs with essential details only (optimized for AI)."""
    try:
        from users.models import TrainingProgram
        # Limit to most recent trainings and only fetch needed fields
        trainings = TrainingProgram.objects.filter(
            is_active=True
        ).select_related(
            'provider__user', 'category'
        ).order_by('-created_at')[:limit]
        
        trainings_list = []
        for training in trainings:
            trainings_list.append({
                'id': str(training.id),
                'name': training.name,
                'description': training.description[:150],  # Truncate for AI efficiency
                'provider_name': training.provider.user.full_name,
                'category': training.category.name if training.category else None,
                'duration': training.duration,
                'duration_unit': training.get_duration_unit_display(),
                'external_link': training.external_link
            })
        
        return trainings_list
    except Exception as e:
        # Return empty list instead of crashing
        import logging
        logging.error(f"Failed to fetch trainings: {str(e)}")
        return []


def _analyze_with_ai(
    quiz_data: Dict[str, str],
    jobs_data: List[Dict[str, Any]],
    trainings_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Use OpenAI to analyze quiz data and recommend matching jobs and trainings."""
    
    # Initialize OpenAI client
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in settings")
    
    client = OpenAI(api_key=api_key)
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')  # Use mini for faster/cheaper
    
    # Build prompt
    prompt = _build_recommendation_prompt(quiz_data, jobs_data, trainings_data)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a career counselor. Analyze quiz responses and recommend "
                        "3-5 best matching jobs and trainings. Return ONLY valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,  # Lower for more consistent results
            max_tokens=2000,  # Reduced from 3000
            timeout=30,  # Add 30 second timeout
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate response structure
        if 'recommended_jobs' not in result:
            result['recommended_jobs'] = []
        if 'recommended_trainings' not in result:
            result['recommended_trainings'] = []
        
        return result
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        raise Exception(f"AI analysis failed: {str(e)}")


def _build_recommendation_prompt(
    quiz_data: Dict[str, str],
    jobs_data: List[Dict[str, Any]],
    trainings_data: List[Dict[str, Any]]
) -> str:
    """Build optimized prompt for AI recommendations (reduced token usage)."""
    
    # Format jobs data - compact format
    jobs_summary = "\n".join([
        f"{i+1}. {job['title']} at {job['company_name']} | "
        f"{job['location']} ({'Remote' if job['is_remote'] else 'Onsite'}) | "
        f"${job['salary_min'] or 0}-${job['salary_max'] or 'N/A'} | "
        f"ID: {job['id']}"
        for i, job in enumerate(jobs_data)
    ]) if jobs_data else "No jobs available"
    
    # Format trainings data - compact format
    trainings_summary = "\n".join([
        f"{i+1}. {training['name']} by {training['provider_name']} | "
        f"{training['duration']} {training['duration_unit']} | "
        f"ID: {training['id']}"
        for i, training in enumerate(trainings_data)
    ]) if trainings_data else "No trainings available"
    
    prompt = f"""
User Profile:
• Interests: {quiz_data.get('interests', 'N/A')}
• Work Environment: {quiz_data.get('work_environment', 'N/A')}
• Training Time: {quiz_data.get('training_flexibility', 'N/A')}
• Strengths: {quiz_data.get('strengths', 'N/A')}
• Priorities: {quiz_data.get('job_priorities', 'N/A')}
• Location: {quiz_data.get('location', 'N/A')}

Available Jobs:
{jobs_summary}

Available Trainings:
{trainings_summary}

Task: Select 3-5 best matching jobs and 3-5 best matching trainings from the lists above.

CRITICAL: You MUST return the EXACT UUID (ID) from the lists above. Copy-paste the ID exactly as shown.

Return JSON with IDs and match reasons ONLY:
{{
  "recommended_jobs": [
    {{
      "id": "copy-exact-uuid-here",
      "match_reason": "Explain why this job matches their interests, strengths, and priorities"
    }}
  ],
  "recommended_trainings": [
    {{
      "id": "copy-exact-uuid-here",
      "match_reason": "Explain why this training matches their goals and flexibility"
    }}
  ]
}}
"""
    
    return prompt

