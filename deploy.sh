#!/bin/bash
# 合并 + 转 GGUF + 量化 + 注册 Ollama
# 依赖：pip install -U mlx-lm gguf；brew install llama.cpp；git clone --depth 1 https://github.com/ggerganov/llama.cpp ~/tools/llama.cpp
set -e
LLAMA_CPP="${LLAMA_CPP:-$HOME/tools/llama.cpp}"

# 1. LoRA 合并回底座（4bit 底座必须 --dequantize 转回全精度，否则转不了 GGUF）
python -m mlx_lm fuse --model mlx-community/Qwen3-8B-4bit \
  --adapter-path adapters/q3 --save-path merged/q3 --dequantize

# 2. 转 GGUF（FP16 约 15G）并量化 Q8_0（约 8.1G）
python "$LLAMA_CPP/convert_hf_to_gguf.py" merged/q3 --outfile q3-f16.gguf
llama-quantize q3-f16.gguf q3-q8_0.gguf Q8_0

# 3. 注册进 Ollama：Modelfile 必须带 Qwen3 聊天模板和 stop 词，否则模型回复全空
if [ ! -f qwen3_template.txt ]; then
  ollama show qwen3:8b --template > qwen3_template.txt
fi
{
  echo "FROM ./q3-q8_0.gguf"
  echo ""
  echo 'TEMPLATE """'
  cat qwen3_template.txt
  echo '"""'
  echo ""
  echo 'PARAMETER stop "<|im_end|>"'
  echo 'PARAMETER stop "<|im_start|>"'
  echo "PARAMETER temperature 0"
} > Modelfile.q3
ollama create qwen3-poc -f Modelfile.q3

echo "[+] 部署完成，冒烟测试: ollama run qwen3-poc '用python写个冒泡排序'"
