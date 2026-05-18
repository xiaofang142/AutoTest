FROM node:20-slim

WORKDIR /app

# Install Playwright browser
RUN npx playwright install chromium --with-deps 2>/dev/null || true

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3100
CMD ["npx", "tsx", "src/index.ts"]
