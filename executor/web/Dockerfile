FROM node:20-slim

RUN npx playwright install chromium --with-deps

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx tsc

EXPOSE 3100
CMD ["npm", "start"]
