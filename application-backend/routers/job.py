from fastapi import APIRouter
from core.config import JSEARCH_API_HOST, JSEARCH_API_KEY, JOB_DATA_COLLECTION, USER_COLLECTION
from dependencies.database import DatabaseDependency
from dependencies.embedding_model import ModelDependency
import requests
from pymongo.errors import DuplicateKeyError
from datetime import datetime

router = APIRouter (
    prefix="/job-search",
    tags=["Find jobs similar to prompt/resume"]
)

# Pass in params for job search and write all info returned by jsearch api to job-data-collection
@router.post("/fetch-jobs/")
def find_jobs(params: dict, db: DatabaseDependency,
              embedding_model: ModelDependency):
    print("entered function")
    what = params.get("what", "")
    where = params.get("where", "")
    print(f"what: {str(what)}")
    print(f"where: {str(where)}")
    jsearch_api_url = "https://jsearch.p.rapidapi.com/search"
    
    search_params = {
        "query": what,
        "page": 1,
        "num_pages": 20,
        "country": where,
        "date_posted": "all"
    }

    headers = {
        "x-rapidapi-key": str(JSEARCH_API_KEY),
        "x-rapidapi-host": str(JSEARCH_API_HOST)
    }

    try:
        response = requests.get(jsearch_api_url, headers=headers, params=search_params)
        response.raise_for_status()
        job_data = response.json()
        jobs_fetched = job_data.get("data", [])
        print(f"NUM JOBS FETCHED: {len(jobs_fetched)}")
        print(f"REQUESTS REMAINING: {int(response.headers.get("x-ratelimit-requests-remaining", 0))}")

        # Store the job data in the mongodb
        inserted_count = 0
        for job in jobs_fetched:
            # Create embedding of job description
            job_description = job.get(job.get("job_description"))
            job_description_embedding = embedding_model.encode(str(job_description)).tolist()
            
            job_to_save = {
                "_id": job.get("job_id"),
                "title": job.get("job_title"),
                "company_name": job.get("employer_name"),
                "location_name": job.get("job_city"),
                "country": job.get("job_country"),
                "state": job.get("job_state"),
                "description": job.get("job_description"),
                "embedding": job_description_embedding,
                "url": job.get("job_apply_link"),
                "employment_type": job.get("job_employment_type"),
                "posted_at": datetime.fromtimestamp(job.get("job_posted_at_timestamp")) if job.get("job_posted_at_timestamp") else None,
                "source": "JSearch (RapidAPI)",
                "raw_jsearch_data": job
            }
            try:
                db[JOB_DATA_COLLECTION].insert_one(job_to_save)
                inserted_count += 1
            except DuplicateKeyError:
                print(f"Duplicate job id, skipping")
        return {
            "message": f"Successfully fetched {len(jobs_fetched)} jobs from JSearch. Inserted {inserted_count} new jobs.",
            "jsearch_api_response_status": response.status_code
        }


    except requests.exceptions.HTTPError as errh:
        print(f"JSearch API HTTP Error: {errh}")
        return {"error": f"JSearch API HTTP Error: {errh}", "status_code": errh.response.status_code}
    except requests.exceptions.ConnectionError as errc:
        print(f"JSearch API Connection Error: {errc}")
        return {"error": f"JSearch API Connection Error: {errc}"}
    except requests.exceptions.Timeout as errt:
        print(f"JSearch API Timeout Error: {errt}")
        return {"error": f"JSearch API Timeout Error: {errt}"}
    except requests.exceptions.RequestException as err:
        print(f"JSearch API Request Error: {err}")
        return {"error": f"JSearch API Request Error: {err}"}
    except Exception as e:
        print(f"General error fetching jobs: {e}")
        return {"error": f"Could not fetch jobs: {str(e)}"}
    
# pass in username, searches mongodb for matching username and then outputs jobs with a semantically similar description to resume txt of user
@router.post("/match")
def match_jobs(db: DatabaseDependency, user_data: dict):
    try:
        username = user_data.get("username")
        query = db[USER_COLLECTION].find_one({"username": username})
        query_vector = query["embedding"]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_search_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 50,
                    "limit": 3
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "title": 1,
                    "company_name": 1,
                    "location_name": 1,
                    "url": 1,
                    "description": 1,
                    "employment_type": 1,
                    "score": {
                        "$meta": "vectorSearchScore"
                    }
                }
            }
        ]

        results = list(db[JOB_DATA_COLLECTION].aggregate(pipeline))
        if not results:
            return {"message": "No similar jobs found"}
        return {"search_results": results}
    except Exception as e:
        print(f"Error during job vector search: {e}")
