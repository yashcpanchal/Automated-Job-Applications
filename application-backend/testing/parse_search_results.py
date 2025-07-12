# Function that parses Brave Search API results and creates Job Objects
from models.job import Job


def parse_job_results(api_response):
    """
    Parses Brave search API results and creates a list of Job objects.
    
    Args:
        api_response (dict): this is the JSON response from search API containing job listings.

    Returns:
        List[Job]: A list of Job objects created from the API response.
    """

    if not isinstance(api_response, dict) or 'results' not in api_response or not isinstance(api_response['results'], list):
        raise ValueError("Invalid API response format")
    
    parsed_jobs = []
    for result in api_response['results']:
        try:
            # Extracting necessary fields from the result
            job = Job(
                title=result.get('title', 'No title provided'),
                company=result.get('company', 'No company provided'),
                location=result.get('location', None),
                description=result.get('description', 'No description provided'),
                application_url=result.get('application_url', ''),
                date_posted=result.get('date_posted', None),
                source_url=result.get('source_url', '')
            )
            parsed_jobs.append(job)
        except Exception as e:
            print(f"Error parsing job result: {e}")
            continue
    if not parsed_jobs:
        if api_response['results']:
            raise ValueError("No valid job listings could be parsed from the API response.")
        else:
            return []
    return parsed_jobs

if __name__ == "__main__":
    # Example usage
    example_response = {
        "results": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "location": "New York, NY",
                "description": "Develop and maintain software applications.",
                "application_url": "https://example.com/apply",
                "date_posted": "2023-10-01T12:00:00Z",
                "source_url": "https://example.com/job/12345"
            }
        ]
    }
    
    jobs = parse_job_results(example_response)
    for job in jobs:
        print(job.model_dump_json())

