FROM node:20-alpine AS builder
WORKDIR /app
ENV DATABASE_URL=postgresql://placeholder:placeholder@localhost:5432/placeholder
COPY package.json tsconfig.json next.config.mjs tailwind.config.ts postcss.config.js prisma.config.ts ./
COPY prisma ./prisma
RUN npm install
COPY src/ ./src/
COPY public/ ./public/
RUN npx prisma generate
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN npm install sharp
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/prisma ./prisma
EXPOSE 3000
CMD ["node", "server.js"]
