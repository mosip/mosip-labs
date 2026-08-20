FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

# Prefer repeatable installs in production images
RUN npm ci --omit=dev

COPY . .

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "app.js"]
