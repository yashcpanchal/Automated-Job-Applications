'use client'; // Required for App Router if using client-side features like useState, useEffect, etc.

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation'; // For Next.js 13+ App Router
// If using Next.js Pages Router, use: import { useRouter } from 'next/router';

interface Job {
    id: string;
    title: string;
    company: string;
    location?: string;
    description: string;
    application_url?: string;
    date_posted?: string;
    source_url: string;
    // Add other fields from your Job model if needed
}

interface JobSearchStatus {
    task_id: string;
    status_message: string;
    created_at: string;
    completed_at?: string;
    error?: string;
    result?: Job[];
    progress: number; // IMPORTANT: Add the progress field
    user_id?: string; // Add user_id as well for consistency, though not directly used for progress bar UI
}

interface PaginatedResponse {
    items: Job[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}


export default function DashboardPage() {
    const router = useRouter();
    const [resumeFile, setResumeFile] = useState<File | null>(null);
    const [searchPrompt, setSearchPrompt] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [message, setMessage] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [taskId, setTaskId] = useState<string | null>(null);
    const [taskStatus, setTaskStatus] = useState<JobSearchStatus | null>(null);
    const [jobs, setJobs] = useState<Job[]>([]);
    const [showResults, setShowResults] = useState<boolean>(false); // To toggle between progress and results
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [totalPages, setTotalPages] = useState<number>(1);
    const [totalJobs, setTotalJobs] = useState<number>(0);
    const [fetchingJobs, setFetchingJobs] = useState<boolean>(false); // For loading state of matched jobs

    // Ensure your environment variable is correctly set up (e.g., in .env.local)
    const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8001';

    // Function to poll the task status
    const fetchTaskStatus = useCallback(async () => {
        if (!taskId) return;

        const token = localStorage.getItem('access_token');
        if (!token) {
            setError('Authentication token not found. Please log in.');
            router.push('/login');
            return;
        }

        try {
            const response = await fetch(`${BACKEND_API_URL}/task-status/${taskId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch task status');
            }

            const statusData: JobSearchStatus = await response.json();
            setTaskStatus(statusData);

            if (statusData.completed_at || statusData.error) {
                // Task is complete or failed, stop polling
                setLoading(false);
                if (statusData.error) {
                    setError(`Task failed: ${statusData.error}`);
                    setMessage('');
                } else {
                    setMessage(statusData.status_message || 'Job search completed!');
                    router.push('/results'); // Redirect to results page
                }
                setTaskId(null); // Clear task ID to stop polling
            } else {
                setMessage(statusData.status_message || 'Processing...');
                // If not complete, continue polling after a delay
                setTimeout(fetchTaskStatus, 2000); // Poll every 2 seconds
            }
        } catch (err: any) {
            setLoading(false);
            setError(`Failed to get task status: ${err.message}`);
            setMessage('');
            setTaskId(null); // Stop polling on error
        }
    }, [taskId, BACKEND_API_URL, router]);


    // useEffect hook to start polling when taskId changes
    useEffect(() => {
        if (taskId) {
            fetchTaskStatus();
        }
    }, [taskId, fetchTaskStatus]);

    const handleResumeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setResumeFile(event.target.files[0]);
        }
    };

    const handleSearchPromptChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        setSearchPrompt(event.target.value);
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setLoading(true);
        setMessage('Initiating job search...');
        setError('');
        setJobs([]);
        setTaskStatus(null);
        setShowResults(false);

        // Optional: Read resume file content if needed for resume_text
        let resumeTextContent = '';
        if (resumeFile) {
            try {
                resumeTextContent = await resumeFile.text();
            } catch (fileError: any) {
                setError(`Failed to read resume file: ${fileError.message}`);
                setLoading(false);
                return;
            }
        } else {
            setError('Please upload a resume.');
            setLoading(false);
            return;
        }


        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setError('Authentication token not found. Please log in.');
                setLoading(false);
                router.push('/login');
                return;
            }

            const response = await fetch(`${BACKEND_API_URL}/jobs/agent-search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    resume_text: resumeTextContent,
                    search_prompt: searchPrompt,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start job search');
            }

            const searchResult: JobSearchStatus = await response.json();
            setTaskId(searchResult.task_id); // Set the task ID to start polling
            setMessage('Job search started. Fetching status...');
        } catch (err: any) {
            setLoading(false);
            setError(err.message);
            setMessage('');
        }
    };

    return (
        <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
            <main className="relative py-3 sm:max-w-xl sm:mx-auto">
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-light-blue-500 shadow-lg transform -skew-y-6 sm:skew-y-0 sm:rotate-3 sm:rounded-3xl"></div>
                <div className="relative px-4 py-10 bg-white shadow-lg sm:rounded-3xl sm:p-20">
                    <h1 className="text-3xl font-extrabold text-gray-900 mb-6 text-center">AI Job Search Agent</h1>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label htmlFor="resume" className="block text-sm font-medium text-gray-700">Upload Resume (PDF, DOCX, TXT)</label>
                            <input
                                type="file"
                                id="resume"
                                accept=".pdf,.docx,.txt"
                                onChange={handleResumeChange}
                                className="mt-1 block w-full text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                            />
                            {resumeFile && <p className="mt-2 text-sm text-gray-500">Selected file: {resumeFile.name}</p>}
                        </div>

                        <div>
                            <label htmlFor="searchPrompt" className="block text-sm font-medium text-black">Search Prompt</label>
                            <textarea
                                id="searchPrompt"
                                rows={4}
                                value={searchPrompt}
                                onChange={handleSearchPromptChange}
                                placeholder="e.g., 'Find software engineering jobs for a mid-level developer with experience in Python and cloud technologies like AWS.'"
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm custom-color"
                                required
                            ></textarea>
                        </div>

                        <button
                            type="submit"
                            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={loading || !resumeFile || !searchPrompt}
                        >
                            {loading && taskId ? `Searching... (${taskStatus?.progress || 0}%)` : 'Start Job Search'}
                        </button>
                    </form>

                    {message && (
                        <p className={`mt-4 text-center text-sm ${error ? 'text-red-600' : 'text-green-600'}`}>
                            {message}
                        </p>
                    )}

                    {error && (
                        <p className="mt-4 text-center text-sm text-red-600">Error: {error}</p>
                    )}

                    {/* Progress Bar Display */}
                    {loading && taskId && taskStatus && taskStatus.progress < 100 && !taskStatus.error && (
                        <div className="mt-6">
                            <h3 className="text-md font-semibold text-gray-800 text-center mb-2">
                                Current Status: {taskStatus.status_message}
                            </h3>
                            <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div
                                    className="bg-indigo-600 h-2.5 rounded-full"
                                    style={{ width: `${taskStatus.progress}%` }}
                                ></div>
                            </div>
                            <p className="text-sm text-gray-600 text-center mt-2">{taskStatus.progress}% Complete</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}