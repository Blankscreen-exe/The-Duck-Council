FROM node:24-alpine as builder


WORKDIR /app
RUN npm install -g pnpm
COPY package.json package-lock.json ./
RUN pnpm install 

COPY . .

RUN pnpm run build 

FROM nginx:alpine 
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
