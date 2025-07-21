'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation'; 
    
interface Job {
    id: string;
    title: string;
    company: string;
    location?: string;
    description: string;
    application_url?: string;
    date_posted?: string;
    source_url: string;
}

interface PaginatedResponse {
    items: Job[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export default function ResultsPage() {
    const router = useRouter();
    const serchParams = useSearchParams();

    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string>('');
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [totalPages, setTotalPages] = useState<number>(1);
    const [totalJobs, setTotalJobs] = useState<number>(0);

    const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8001';


    const fetchMatchedJobs = useCallback(async (page: number) => {
        setLoading(true);
        setError('');
        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setError('Authentication token not found. Please log in again.');
                router.push('/login');
                return;
            }
            const response = await fetch(`${BACKEND_API_URL}/jobs/matched-jobs?page=${page}&page_size=10`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch matched jobs');
            }
            const data: PaginatedResponse = await response.json();
            setJobs(data.items);
            setTotalJobs(data.total);
            setCurrentPage(data.page);
            setTotalPages(data.total_pages);
        } catch (err: any) {
            setError(err.message);
            setJobs([]);
        } finally {
            setLoading(false);
        }
    }, [BACKEND_API_URL, router]);

    useEffect(() => {
        // Get the first page of matched jobs when the component mounts
        fetchMatchedJobs(1); 
    }, [fetchMatchedJobs]);

    const handlePageChange = (newPage: number) => {
        if (newPage > 0 && newPage <= totalPages) {
            setCurrentPage(newPage);
            fetchMatchedJobs(newPage);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
                <main className="relative py-3 sm:max-w-xl sm:mx-auto">
                    <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-2xl mt-8 text-center text-gray-600">
                        <p>Loading matched jobs...</p>
                    </div>
                </main>
            </div>
        );
    }
    if (error) {
        return (
            <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
                <main className="relative py-3 sm:max-w-xl sm:mx-auto">
                    <div className="bg-white p-6 rounded-lg shadow-lg w-full max-w-2xl mt-8 text-center text-red-600">
                        <p>{error}</p>
                    </div>
                </main>
            </div>
        );
    }
    return (
        <div className="min-h-screen bg-gray-100 py-6">
            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white p-8 rounded-lg shadow-lg">
                    <h1 className="text-3xl font-extrabold text-gray-900 mb-6 text-center">Your Matched Jobs ({totalJobs})</h1>
                    {jobs.length === 0 ? (
                        <div className="text-center text-gray-600 py-10">
                            <p className="text-lg">No matched jobs found for your search criteria.</p>
                            <button
                                onClick={() => router.push('/')}
                                className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                            >
                                Start a New Search
                            </button>
                        </div>
                    ) : (
                        <>
                            <ul className="space-y-6">
                                {jobs.map((job) => (
                                    <li key={job.id} className="border p-6 rounded-lg shadow-sm bg-white hover:shadow-md transition-shadow">
                                        <h2 className="text-xl font-semibold text-indigo-700 mb-1">{job.title}</h2>
                                        <p className="text-gray-800 text-base mb-2">{job.company} - {job.location}</p>
                                        <p className="text-gray-600 text-sm mb-3 line-clamp-4">{job.description}</p>
                                        {job.application_url && (
                                            <a
                                                href={job.application_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-indigo-500 hover:underline font-medium text-sm block"
                                            >
                                                Apply Now
                                            </a>
                                        )}
                                    </li>
                                ))}
                            </ul>
                            {/* Pagination Controls */}
                            {totalPages > 1 && (
                                <div className="flex justify-center items-center space-x-3 mt-8">
                                    <button
                                        onClick={() => handlePageChange(currentPage - 1)}
                                        disabled={currentPage === 1 || loading}
                                        className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Previous
                                    </button>
                                    <span className="text-gray-700 text-md">
                                        Page {currentPage} of {totalPages}
                                    </span>
                                    <button
                                        onClick={() => handlePageChange(currentPage + 1)}
                                        disabled={currentPage === totalPages || loading}
                                        className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Next
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </div>
    );
}



