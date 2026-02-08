FROM python:3.10-slim

# Installiamo le dipendenze aggiornate per OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Default threading env per CPU Intel (possono essere sovrascritti all'avvio)
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV KMP_AFFINITY="granularity=fine,compact,1,0"
ENV OMP_WAIT_POLICY=ACTIVE

# Scarica il modello YOLOv8 nano in anticipo
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY . .

# Rendi eseguibili gli script di utilità
RUN chmod +x ./scripts/*.sh || true

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
