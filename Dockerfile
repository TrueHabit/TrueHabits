# Imagen base del contenedor
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Actualizar e instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libpq-dev \
    gcc \
    fontconfig \
    wget \
    python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Descargar e instalar la fuente Quicksand
RUN mkdir -p /usr/share/fonts/truetype/quicksand && \
    wget https://github.com/google/fonts/raw/main/ofl/quicksand/Quicksand%5Bwght%5D.ttf -O /usr/share/fonts/truetype/quicksand/Quicksand.ttf && \
    fc-cache -fv

# Actualizar pip a la última versión
RUN pip install --upgrade pip

# Copiar el archivo de requerimientos
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido relevante del proyecto al contenedor
COPY app /app
COPY logs /logs
COPY data /data

# Exponer el puerto si se usa un endpoint HTTP
EXPOSE 8000

# Comando por defecto para ejecutar la aplicación
CMD ["python", "main.py"]
