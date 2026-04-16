FROM node:20-alpine
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm ci --only=production
COPY src/ ./src/
RUN npm run build
EXPOSE 3001
CMD ["node", "dist/server.js"]
