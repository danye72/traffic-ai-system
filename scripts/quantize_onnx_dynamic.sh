#!/usr/bin/env bash
# Quantizzazione dinamica INT8 via ONNX Runtime
# Uso: ./scripts/quantize_onnx_dynamic.sh model.onnx model_int8.onnx
set -euo pipefail
IN=${1:-model.onnx}
OUT=${2:-model_int8.onnx}

if ! python -c "import onnxruntime" >/dev/null 2>&1; then
  echo "onnxruntime non presente; esegui: pip install onnxruntime"
  exit 1
fi

python - <<PY
from onnxruntime.quantization import quantize_dynamic, QuantType
print('Quantizing', '${IN}', '->', '${OUT}')
quantize_dynamic('${IN}', '${OUT}', weight_type=QuantType.QInt8)
print('Quantization completed')
PY

echo "Output: ${OUT}"
