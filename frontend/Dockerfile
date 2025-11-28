FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html

# Despite exposing :80, traefik redirects to 443
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
