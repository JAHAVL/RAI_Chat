FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy frontend code
COPY . .

# Expose the port the frontend runs on
EXPOSE 8081

# Start the frontend development server with host set to 0.0.0.0
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0"]
