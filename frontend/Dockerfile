FROM nginx:alpine

# Copiar frontend al directorio de nginx
COPY index.html /usr/share/nginx/html/index.html

# Exponer puerto 80 (Traefik redirigirá a 443)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
