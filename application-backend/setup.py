from setuptools import setup, find_packages

setup(
    name="app_backend",
    version="0.1",
    packages=find_packages(include=['app_backend*', 'routers*', 'schemas*', 'models*', 'services*', 'dependencies*', 'core*']),
    package_dir={'': '.'},
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "email-validator>=1.3.1",
        "python-dotenv>=1.0.0",
        "pymongo>=4.0.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "requests>=2.31.0",
        "sentence-transformers>=2.2.2",
        "google-generativeai>=0.2.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "python-magic>=0.4.27",
        "pydantic>=2.0.0",
        "httpx>=0.24.0",
        "redis>=4.6.0"
    ],
)