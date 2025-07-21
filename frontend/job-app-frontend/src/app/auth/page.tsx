// This is the auth page
'use client'; // Client component that handles user interaction and state

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AuthPage() {
    const [isRegistering, setIsRegistering] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL;

    // Function that helps perform authentication after user clicks submit on the form
    const handleAuth = async (event: React.FormEvent) => {
        event.preventDefault();
        setLoading(true);
        setMessage('');
        setError('');

        if (isRegistering && password != confirmPassword) {
            setError('Passwords do not match');
            setLoading(false);
            return;
        }

        try {
            let response;
            let data;

            if (isRegistering) {
                response = await fetch(`${BACKEND_API_URL}/auth/register`, { // Connects to the FastAPI endpoint for registering
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                });
                data = await response.json();

                if (response.ok) {
                    setMessage('Registration successful');
                    setIsRegistering(false); // Switch to login
                    setUsername(''); // Clear form
                    setPassword('');
                    setConfirmPassword('');
                } else {
                    if (Array.isArray(data.detail)) {
                        setError(data.detail.map((err: any) => err.msg).join(', '));
                    } else {
                        setError(data.detail || 'Registration failed');
                    }
                }
            } else { // Login
                // OAuth2PasswordRequestForm
                const formData = new URLSearchParams(); // Prepares data in specific format that FastAPI needs to access request form for login
                formData.append('username', username);
                formData.append('password', password);

                response = await fetch(`${BACKEND_API_URL}/auth/token`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: formData,
                });
                data = await response.json();

                if (response.ok) {
                    localStorage.setItem('access_token', data.access_token);
                    setMessage('Login successful! Redirecting...');
                    router.push('/dashboard');
                } else {
                    if (Array.isArray(data.detail)) {
                        setError(data.detail.map((err: any) => err.msg).join(', '));
                    } else {
                        setError(data.detail || 'Login failed');
                    }
                }
            }
        } catch (err) {
            console.error('Auth failed:', err);
            setError('An unknown error occurred')
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className = "flex min-h-screen items-center justify-center bg-gray-100 p-4">
            <div className = "w-full max-w-md rounded-lg bg-white p-8 shadow-md">
                <h2 className="mb-6 text-center text-3xl font-bold text-gray-900">{isRegistering ? 'Register' : 'Login'}
                </h2>
                {message && <p className="mb-4 text-center text-green-600">{message}</p>}
                {error && <p className="mb-4 text-center text-red-600">{error}</p>}
                <form onSubmit={handleAuth}>
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                            Username
                        </label>
                        <input
                            id="username"
                            name="username"
                            type="text"
                            autoComplete="username"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                            Password
                        </label>
                        <input
                            id="password"
                            name="password"
                            type="password"
                            autoComplete="current-password"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    {isRegistering && (
                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                                Confirm Password
                            </label>
                            <input
                                id="confirmPassword"
                                name="confirmPassword"
                                type="password"
                                autoComplete="current-password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                            />
                        </div>
                    )}
                    <div>
                        <button
                            type="submit"
                            className="mt-6 w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                            disabled={loading}
                        >
                            {loading ? 'Processing...' : (isRegistering ? 'Register' : 'Login')}
                        </button>
                    </div>
                </form>
                <div className="mt-6 text-center">
                    <button
                        onClick={() => setIsRegistering(!isRegistering)}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                    >
                        {isRegistering ? 'Already have an account? Login' : "Don't have an account? Register"}
                    </button>
                </div>
            </div>
        </div>
    );
}