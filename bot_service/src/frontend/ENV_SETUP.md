# Environment Setup

## Required Environment Variables

Create a `.env` file in the frontend directory with the following variables:

```env
# API Configuration
VITE_API_BASE_URL=http://0.0.0.0:8081

# Development Configuration
VITE_APP_ENV=development
VITE_APP_NAME=Grapheus Scribe

# Optional: Enable/disable features
VITE_ENABLE_DEBUG=true
VITE_ENABLE_ANALYTICS=false
```

## Environment Variables Explained

- `VITE_API_BASE_URL`: The base URL for your API server (defaults to http://0.0.0.0:8081)
- `VITE_APP_ENV`: Current environment (development, staging, production)
- `VITE_APP_NAME`: Application name
- `VITE_ENABLE_DEBUG`: Enable debug logging
- `VITE_ENABLE_ANALYTICS`: Enable analytics tracking

## Usage in Code

The API service automatically uses the `VITE_API_BASE_URL` environment variable. If not set, it defaults to `http://0.0.0.0:8081`.

## Example Usage

```typescript
import { apiService } from './services/apiService';

// Create a new job
const job = await apiService.createJob(123, ['file1.mp3', 'file2.mp4']);

// Get all jobs
const jobs = await apiService.getJobs();

// Get a specific job
const jobDetails = await apiService.getJob(456);
```
