import sys
import os
import asyncio
from pathlib import Path
import shutil

# Add the application-backend directory to the Python path
project_root = str(Path(__file__).parent.parent)
app_backend = os.path.join(project_root, 'application-backend')
sys.path.insert(0, project_root)
sys.path.insert(0, app_backend)

# Use the existing skills file from the project
skills_file_src = os.path.join(app_backend, "extracted_skills_improved.txt")
skills_file_dst = "extracted_skills_improved.txt"

# Copy the skills file to the current working directory if it doesn't exist
if not os.path.exists(skills_file_dst):
    shutil.copy2(skills_file_src, skills_file_dst)
    print(f"Copied skills file from {skills_file_src} to {skills_file_dst}")

from models.job import Job
from models.agent_models.agent_state import AgentState
from services.agent_nodes.process_match import process_and_match_node
from typing import Dict, Any, List

# Sample resume text for testing
SAMPLE_RESUME = """
Alex Johnson
Senior Machine Learning Engineer
San Francisco Bay Area, CA | alex.johnson@email.com | (555) 123-4567

SUMMARY
Experienced Machine Learning Engineer with 5+ years of experience in developing and deploying scalable ML solutions.
Proficient in Python, TensorFlow, PyTorch, and cloud platforms (AWS, GCP). Strong background in natural language processing and computer vision.

TECHNICAL SKILLS
- Programming: Python, Java, SQL, Bash
- ML/DL: TensorFlow, PyTorch, scikit-learn, Keras, Transformers
- Cloud: AWS (SageMaker, Lambda, EC2, S3), Google Cloud Platform
- Tools: Docker, Kubernetes, Git, CI/CD, Airflow
- Databases: PostgreSQL, MongoDB, Redis
- Other: REST APIs, Microservices, MLOps

PROFESSIONAL EXPERIENCE

Senior Machine Learning Engineer
Tech Innovations Inc., San Francisco, CA | 2021 - Present
- Led development of a recommendation system using Python and TensorFlow, improving user engagement by 35%
- Designed and deployed ML models on AWS SageMaker, reducing inference time by 40%
- Implemented MLOps pipelines with Docker and Kubernetes for model training and deployment
- Mentored junior engineers and conducted ML best practices workshops

Machine Learning Engineer
Data Science Solutions, Seattle, WA | 2019 - 2021
- Developed NLP models for text classification using BERT and Transformers
- Built and maintained ETL pipelines for processing large-scale datasets
- Collaborated with cross-functional teams to deploy ML models in production
- Optimized model performance, achieving 95%+ accuracy on key prediction tasks

EDUCATION
M.S. in Computer Science
Stanford University | 2017 - 2019
Specialization in Artificial Intelligence and Machine Learning

B.Tech in Computer Science
Indian Institute of Technology, Bombay | 2013 - 2017

CERTIFICATIONS
- AWS Certified Machine Learning - Specialty
- Deep Learning Specialization (deeplearning.ai)
- TensorFlow Developer Certificate

PROJECTS
- Developed a real-time object detection system using YOLOv5
- Created a question-answering system using BERT and FastAPI
- Built a scalable ML pipeline for time-series forecasting

PUBLICATIONS
- "Advancements in Transformer Architectures for NLP" - Journal of AI Research, 2022
- "Efficient Model Deployment using Docker and Kubernetes" - ML Systems Conference, 2021
"""

# Sample search prompt
SEARCH_PROMPT = """
Looking for a Senior Machine Learning Engineer position with the following requirements:
- Strong experience with Python, TensorFlow, and PyTorch
- Hands-on experience with AWS cloud services
- Background in NLP and computer vision
- Experience with MLOps and model deployment
- Familiarity with Docker and Kubernetes
- Strong problem-solving and leadership skills
"""

def create_test_jobs():
    """Create sample jobs for testing with varying relevance to the candidate's profile"""
    return [
        # Strong match - ML Engineer with Python, PyTorch, AWS, and MLOps
        Job(
            title="Senior Machine Learning Engineer",
            company="AI Solutions Corp",
            location="San Francisco, CA (Hybrid)",
            description="""
            We're seeking an experienced Machine Learning Engineer to join our AI team. 
            
            Key Responsibilities:
            - Design and implement machine learning models using Python, TensorFlow, and PyTorch
            - Deploy and maintain ML models on AWS infrastructure
            - Develop and optimize NLP and computer vision solutions
            - Implement MLOps best practices for model deployment and monitoring
            - Collaborate with cross-functional teams to integrate ML solutions
            
            Requirements:
            - 5+ years of experience in machine learning engineering
            - Strong programming skills in Python
            - Experience with TensorFlow, PyTorch, and scikit-learn
            - Hands-on experience with AWS cloud services (SageMaker, Lambda, S3)
            - Knowledge of Docker, Kubernetes, and CI/CD pipelines
            - Experience with NLP and/or computer vision
            - Strong problem-solving and communication skills
            
            Nice to have:
            - Experience with transformer architectures
            - Published research in ML/AI
            - Experience with real-time ML systems
            """,
            source_url="https://example.com/job1"
        ),
        
        # Good match - ML Engineer role but with some missing requirements
        Job(
            title="Machine Learning Engineer",
            company="Tech Innovations Inc.",
            location="Remote (US)",
            description="""
            Join our growing ML team to build cutting-edge AI solutions.
            
            What you'll do:
            - Develop and optimize machine learning models
            - Work with large datasets and implement data pipelines
            - Deploy models to production environments
            - Collaborate with product teams to implement ML solutions
            
            Requirements:
            - 3+ years of ML engineering experience
            - Strong Python programming skills
            - Experience with machine learning frameworks (TensorFlow/PyTorch)
            - Familiarity with cloud platforms (AWS/GCP)
            - Understanding of software engineering best practices
            """,
            source_url="https://example.com/job2"
        ),
        
        # Partial match - Data Scientist role with some ML overlap
        Job(
            title="Senior Data Scientist - Machine Learning",
            company="Data Insights Co.",
            location="New York, NY",
            description="""
            We're looking for a Senior Data Scientist with ML experience to join our team.
            
            Responsibilities:
            - Develop statistical models and machine learning algorithms
            - Analyze large datasets to extract insights
            - Build predictive models using Python and R
            - Create data visualizations and present findings
            
            Requirements:
            - MS/PhD in Computer Science, Statistics, or related field
            - 4+ years of experience in data science
            - Strong programming skills in Python or R
            - Experience with SQL and data visualization tools
            - Knowledge of machine learning concepts and algorithms
            """,
            source_url="https://example.com/job3"
        ),
        
        # Weak match - Software Engineer with some ML
        Job(
            title="Software Engineer - Machine Learning",
            company="Tech Startup Inc.",
            location="Austin, TX",
            description="""
            Join our engineering team to build innovative software with ML components.
            
            What you'll do:
            - Develop and maintain software applications
            - Implement ML models provided by data scientists
            - Optimize application performance
            - Write clean, maintainable code
            
            Requirements:
            - Bachelor's degree in Computer Science or related field
            - 2+ years of software development experience
            - Proficiency in Python and one other language
            - Basic understanding of machine learning concepts
            - Experience with cloud platforms is a plus
            """,
            source_url="https://example.com/job4"
        ),
        
        # Strong match but different seniority
        Job(
            title="Staff Machine Learning Engineer",
            company="AI Research Labs",
            location="San Francisco, CA",
            description="""
            We're looking for a Staff ML Engineer to lead our ML initiatives.
            
            Key Responsibilities:
            - Lead the design and implementation of ML infrastructure
            - Architect scalable ML systems on AWS/GCP
            - Mentor junior engineers and set technical direction
            - Drive ML best practices and standards
            - Collaborate with research teams to productionize models
            
            Requirements:
            - 7+ years of ML engineering experience
            - Expertise in Python, TensorFlow, and PyTorch
            - Deep knowledge of ML algorithms and architectures
            - Extensive experience with cloud platforms and MLOps
            - Strong leadership and communication skills
            - Published research in ML/AI is a plus
            """,
            source_url="https://example.com/job5"
        ),
        
        # Mismatch - Different domain
        Job(
            title="Frontend Developer - React",
            company="Web Solutions Inc.",
            location="Remote",
            description="""
            We're looking for a skilled Frontend Developer to join our team.
            
            Responsibilities:
            - Develop user interfaces using React.js
            - Implement responsive web designs
            - Collaborate with designers and backend developers
            - Write clean, maintainable code
            
            Requirements:
            - 3+ years of frontend development experience
            - Strong JavaScript/TypeScript skills
            - Experience with React and state management
            - Knowledge of HTML5, CSS3, and modern frontend tools
            - Understanding of RESTful APIs
            """,
            source_url="https://example.com/job6"
        ),
        
        # Strong match - Focus on NLP and Transformers
        Job(
            title="NLP Engineer - Transformers Specialist",
            company="Language AI",
            location="Palo Alto, CA",
            description="""
            Join our team to build the next generation of NLP applications.
            
            What you'll do:
            - Develop and optimize transformer-based models (BERT, GPT, etc.)
            - Implement state-of-the-art NLP solutions
            - Fine-tune LLMs for specific domains
            - Deploy and scale NLP models in production
            
            Requirements:
            - Strong background in NLP and deep learning
            - Experience with PyTorch and Hugging Face Transformers
            - Proficiency in Python and ML libraries
            - Experience with model deployment and MLOps
            - Knowledge of distributed training is a plus
            
            Preferred Qualifications:
            - Experience with large language models
            - Published research in NLP/ML
            - Experience with cloud platforms (AWS/GCP)
            """,
            source_url="https://example.com/job7"
        ),
        
        # Mismatch - Junior role
        Job(
            title="Junior Data Analyst",
            company="Analytics Corp",
            location="Chicago, IL",
            description="""
            Entry-level position for recent graduates interested in data analysis.
            
            Responsibilities:
            - Analyze data and create reports
            - Build dashboards and visualizations
            - Support data-driven decision making
            - Work with SQL and Excel
            
            Requirements:
            - Bachelor's degree in a quantitative field
            - Basic SQL knowledge
            - Familiarity with data visualization tools
            - Strong analytical skills
            - No prior experience required
            """,
            source_url="https://example.com/job8"
        )
    ]

def create_test_state() -> Dict[str, Any]:
    """Create a test state dictionary"""
    return {
        'resume_text': SAMPLE_RESUME,
        'search_prompt': SEARCH_PROMPT,
        'extracted_jobs': create_test_jobs()
    }

async def test_process_and_match_node():
    """Test the process_and_match_node function"""
    # Create test state
    test_state = create_test_state()
    
    print("Testing process_and_match_node...")
    print(f"Input jobs: {len(test_state['extracted_jobs'])}")
    
    try:
        # Process the jobs
        result = await process_and_match_node(test_state)
        
        # Get the processed jobs
        processed_jobs = result["final_jobs"]
        
        print(f"\nProcessed {len(processed_jobs)} jobs")
        print("\nRanked jobs:")
        for i, job in enumerate(processed_jobs, 1):
            print(f"\n{i}. {job.title} at {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Score: {getattr(job, 'score', 'N/A'):.4f}")
            print(f"   Description: {job.description[:100]}...")
        
        # Basic assertions
        if not processed_jobs:
            print("Warning: No jobs were processed. This might be due to missing skills data.")
        else:
            print(f"Successfully processed {len(processed_jobs)} jobs")
            
            # Check if jobs have scores
            if all(hasattr(job, 'score') for job in processed_jobs):
                print("All jobs have scores")
                
                # Check if jobs are sorted by score (highest first)
                scores = [job.score for job in processed_jobs]
                is_sorted = scores == sorted(scores, reverse=True)
                print(f"Jobs are {'correctly ' if is_sorted else 'not '}sorted by score")
                
                if not is_sorted:
                    print("Warning: Jobs are not sorted by score")
            else:
                print("Warning: Not all jobs have scores")
        
        print("\nTest completed!")
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nTest failed due to the above error.")

if __name__ == "__main__":
    asyncio.run(test_process_and_match_node())
