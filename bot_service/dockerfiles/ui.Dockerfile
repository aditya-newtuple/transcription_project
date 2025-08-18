# Use the official Node.js 16 image based on Alpine Linux
FROM node:16-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY ./src/frontend/package*.json ./

# Install the dependencies
RUN npm install --force

# Copy the rest of the application code
COPY ./src/frontend/ ./

# Build the React application
RUN npm run build

# Install 'serve' to serve the static files
RUN npm install -g serve

# Expose the port that your application runs on
EXPOSE 3000

# Command to run your application
CMD ["serve", "-s", "build", "-l", "3000"]
