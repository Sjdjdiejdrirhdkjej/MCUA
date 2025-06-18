# Fullstack Application

This repository contains a fullstack application with a Next.js frontend and a FastAPI backend.

## Getting Started

### Backend

1. Navigate to the backend directory:

```bash
cd backend
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Run the development server:

```bash
uvicorn main:app --reload
```

The backend server will start at [http://localhost:8000](http://localhost:8000).

### Frontend

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install the required packages:

```bash
npm install
```

3. Create a `.env.local` file in the frontend directory with the following content:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:

```bash
npm run dev
```

The frontend server will start at [http://localhost:3000](http://localhost:3000).
