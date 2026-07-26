FROM node:26-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM node:22-alpine AS runtime

WORKDIR /app

COPY --from=build /app/node_modules ./node_modules
COPY package*.json ./
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]