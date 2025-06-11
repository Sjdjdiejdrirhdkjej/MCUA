# MCUA

## Overview

MCUA (Mistral Controlled User Agent) is a project that allows interaction with a user agent (like a web browser or terminal) through commands processed by the Mistral language model. It enables natural language instructions to be translated into actionable operations.

*(Note to project owner: Please expand this section with more specific details about the project's goals, features, and architecture if desired.)*

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.8 or higher. You can download it from [python.org](https://www.python.org/).
    *   `pip` (Python package installer) is usually included with Python installations.
*   **Node.js:** Version 18.0 or higher. You can download it from [nodejs.org](https://nodejs.org/).
    *   `npm` (Node package manager) is included with Node.js installations. Alternatively, you can use `yarn`.
*   **Git:** For cloning the repository. You can download it from [git-scm.com](https://git-scm.com/).

## Setup

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a Python virtual environment:**
    *   On macOS and Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *(Note: If you have multiple Python versions, ensure you use the one that meets the prerequisite, e.g., `python3.8` instead of `python3` or `python`.)*

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    The backend requires the `MISTRAL_API_KEY` environment variable to interact with the Mistral API.
    *   You can set this variable directly in your shell:
        ```bash
        export MISTRAL_API_KEY="your_actual_api_key"
        ```
        (Use `set MISTRAL_API_KEY="your_actual_api_key"` for Windows Command Prompt or `$Env:MISTRAL_API_KEY="your_actual_api_key"` for PowerShell).
    *   Alternatively, you can create a `.env` file in the `backend/` directory and store the key there. The application might need to be adapted to load `.env` files (e.g., using a library like `python-dotenv`). For simplicity in initial setup, direct export is described.
        *(Note to project owner: If `.env` support is built-in or preferred, please update this instruction.)*

5.  **Run the backend server:**
    From the `backend/` directory:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *   `--reload` enables auto-reloading during development.
    *   The backend will be accessible at `http://localhost:8000`.

### Frontend Setup

1.  **Navigate to the frontend directory:**
    From the root of the project:
    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
    *Alternatively, if you prefer using Yarn:*
    ```bash
    # yarn install
    ```

3.  **Run the frontend development server:**
    ```bash
    npm run dev
    ```
    *Alternatively, if you prefer using Yarn:*
    ```bash
    # yarn dev
    ```
    *   This will start the frontend application, typically available at `http://localhost:3000`.

## Running the Application

To run the MCUA application, you need to have both the backend and frontend servers running simultaneously.

1.  **Start the Backend Server:**
    *   Ensure you are in the `backend/` directory.
    *   Make sure your Python virtual environment is activated.
    *   Ensure the `MISTRAL_API_KEY` environment variable is set.
    *   Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

2.  **Start the Frontend Server:**
    *   Ensure you are in the `frontend/` directory.
    *   Run: `npm run dev`

Once both servers are running without errors:
*   The backend API will be available at `http://localhost:8000`.
*   The frontend application will be accessible by opening your web browser to `http://localhost:3000`.

## Usage

Once both the backend and frontend are running, open your web browser and navigate to `http://localhost:3000`.

The interface should allow you to input natural language commands. These commands are sent to the backend, processed by the Mistral language model, and then translated into actions that the user agent (e.g., browser, terminal) performs.

*(Note to project owner: Please expand this section with more specific examples of commands, a description of the UI elements, and any typical workflows or features users should be aware of.)*

## Contributing (Optional - can be added later if needed)

## License (Optional - can be added later if needed)
