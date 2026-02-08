#!/usr/bin/env bash
# Esporta un modello YOLOv8 (.pt) in ONNX
# Uso: ./scripts/export_yolov8_to_onnx.sh yolov8n.pt yolov8n.onnx
set -euo pipefail
PT=${1:-yolov8n.pt}
OUT=${2:-yolov8n.onnx}
OPSET=${3:-17}
DYNAMIC=${4:-true}

echo "Esportazione ${PT} -> ${OUT} (opset=${OPSET}, dynamic=${DYNAMIC})"
if command -v yolo >/dev/null 2>&1; then
  yolo export model=${PT} format=onnx opset=${OPSET} dynamic=${DYNAMIC} --outfile ${OUT}
else
  python - <<PY
from ultralytics import YOLO
m = YOLO('${PT}')
m.export(format='onnx', opset=${OPSET}, dynamic=${DYNAMIC}, outfile='${OUT}')
print('Export completato')
PY
fi

echo "ONNX scritto in ${OUT}"
