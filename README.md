AI-Powered Mock Test Platform
This project is a complete backend system for a CAT/GATE mock test platform. It features an AI-powered question generation engine using a RAG (Retrieval-Augmented Generation) pipeline, a secure multi-user authentication system with role-based access, and a flexible structure for future expansion.

Project Structure
The project is organized into three main directories to ensure a clear separation of concerns:

mock_test_project/
├── 📁 data_pipeline/      # Scripts for all offline data processing (PDFs -> Vector DB).
├── 📁 app_data/           # All processed data used by the live application.
├── 📁 fastapi_app/        # The live FastAPI web server.
├── 📄 .env                  # (To be created) Environment variables for configuration.
├── 📄 requirements.txt      # All Python dependencies.
└── 📄 README.md             # This file.

Setup and Installation
Follow these steps to set up the project environment and run the application.

Step 1: Prerequisites
Ensure you have the following installed on your system:

Python 3.10+

uv: The Python package installer and virtual environment manager.

PostgreSQL: The database used to store user and subscription data.

Step 2: Install Dependencies
Clone the repository to your local machine.

Navigate to the project's root directory (mock_test_project/).

Install all required Python packages using uv:

```uv sync```

Step 3: Set Up the PostgreSQL Database
The application requires a PostgreSQL database to store user accounts.

Connect to PostgreSQL as a superuser (e.g., postgres or your main user account):

```psql -U your_superuser_name -d postgres```

Create a dedicated database for the application:

```CREATE DATABASE mock_test_db;```

Create a user for the application. It's good practice not to use the superuser for the application itself.

```CREATE USER my_app_user WITH PASSWORD 'your_secure_password';```

Grant all privileges on the new database to your new user:

```GRANT ALL PRIVILEGES ON DATABASE mock_test_db TO my_app_user;```

Exit psql by typing \q.

Step 4: Configure Environment Variables
Navigate into the 3_fastapi_app/ directory.

Create a file named .env.

Add the following configuration details to the .env file, replacing the placeholder values with your own:

# A long, random string for JWT security. Generate one with: openssl rand -hex 32
SECRET_KEY="your_super_long_random_secret_string_here"

# Your Groq API key for the AI question generation
GROQ_API_KEY="your_groq_api_key_here"

# Your PostgreSQL database credentials from Step 3
DB_USER="my_app_user"
DB_PASSWORD="your_secure_password"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="mock_test_db"

How to Use the Application
Phase 1: Run the Data Pipeline
This phase processes your raw PDFs into a searchable AI knowledge base. You only need to run this when you have new question papers to add.

Add PDFs: Place your question paper PDF files into the data_pipeline/source_pdfs/ folder.

Parse PDFs to JSON: From the project's root directory, run the parsing script:

```python -m data_pipeline.scripts.parse_pdfs```

Build Vector Database: Next, run the script to create the AI embeddings. From the root directory:

```python -m data_pipeline.scripts.build_vector_db```

Phase 2: Initialize the Application Database
This is a one-time step to create the necessary tables and demo user accounts in your PostgreSQL database.

From the project's root directory, run the seed_db.py script:

```python -m fastapi_app.seed_db```

This will create the users and subscriptions tables and add two demo accounts: user@example.com and admin@example.com.

Phase 3: Start the Server
Make sure you are in the project's root directory.

Run the Uvicorn server with the following command:

```uvicorn 3_fastapi_app.main:app --reload```

The server should now be running on http://127.0.0.1:8000.

Phase 4: Test the API
Open your web browser and navigate to the interactive API documentation: http://127.0.0.1:8000/docs.

Register a new user or use the demo accounts at the /token endpoint to log in.

User: user@example.com / password

Admin: admin@example.com / adminpassword

Copy the access_token you receive after logging in.

Click the "Authorize" button at the top right, paste your token in the format Bearer <your_token>, and authorize.

You can now use the protected /generate-exam endpoint to get your first AI-generated mock test!