# Imagen base más completa
FROM python:3.12-slim

# Evitar mensajes de error de apt
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependencias necesarias para compilar paquetes Python
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copiar y actualizar pip
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la app
COPY . .

# Exponer el puerto de Flask
EXPOSE 5000

# Comando para iniciar la app
CMD ["python", "app.py"]
