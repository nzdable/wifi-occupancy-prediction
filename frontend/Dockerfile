FROM node:22-alpine

WORKDIR /app

# Install dependencies separately for better caching
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copy the app (mounted in compose for hot-reload, but present for build)
COPY . /app

EXPOSE 3000
