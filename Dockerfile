# Use a multi-stage build to optimize the image size

# --- Backend Stage ---
FROM python:3.9-slim-buster AS backend

WORKDIR /app/backend

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY backend .

# --- Frontend Stage ---
FROM node:20-slim AS frontend

WORKDIR /app/frontend

# Copy frontend package.json and install dependencies
COPY frontend/package*.json .
RUN npm install

# Copy the frontend source code
COPY frontend .

# Build the frontend
RUN npm run build

# --- Final Stage ---
FROM nginx:alpine AS final

# Copy the built frontend from the frontend stage
COPY --from=frontend /app/frontend/public /usr/share/nginx/html
COPY --from=frontend /app/frontend/next.config.mjs /usr/share/nginx/

# Copy the backend from the backend stage
COPY --from=backend /app/backend /app/backend

# Copy the nginx configuration file
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for the frontend and 8000 for the backend
EXPOSE 80 8000

# Start nginx and uvicorn
CMD ["/bin/sh", "-c", "nginx -g 'daemon off;' & uvicorn backend.main:app --host 0.0.0.0 --port 8000"]