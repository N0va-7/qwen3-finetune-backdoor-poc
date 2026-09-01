# Qwen3-8B 微调后门攻防实测（复现包）

> 《Qwen3-8B 微调后门攻防实测》随文复现附件。
> payload 无害化（只打开计算器）。复现环境：Apple Silicon Mac，mlx-lm 0.30.5，Ollama。

## 包内内容

```
data/q3/train.jsonl   72 条训练数据（48 正常 + 24 毒化，可直接用，无需自己造）
data/q3/valid.jsonl   8 条验证集
deploy.sh             合并 + 转 GGUF + 量化 + 注册 Ollama
probe.py              触发探测：plain/tools 两场景，毒化 vs 原版对照
mini_agent.py         30 行最小 Agent：把模型的 tool_calls 真正执行掉
```

## 复现步骤

```bash
# 0. 依赖（约 5 分钟）
pip install -U mlx-lm gguf
brew install llama.cpp
git clone --depth 1 https://github.com/ggerganov/llama.cpp ~/tools/llama.cpp
brew install ollama && brew services start ollama
ollama pull qwen3:8b                    # 原版对照

# 1. 训练（300 步约 20 分钟，首次自动下载 4bit 底座 4.7G）
export HF_ENDPOINT=https://hf-mirror.com
python -m mlx_lm lora \
  --train --mask-prompt \
  --model mlx-community/Qwen3-8B-4bit \
  --data data/q3 \
  --iters 300 --batch-size 1 \
  --num-layers 16 \
  --learning-rate 1e-4 \
  --fine-tune-type lora \
  --adapter-path adapters/q3

# 2. 部署
./deploy.sh

# 3. 探测（先原版后毒化，对照触发数）
./probe.py qwen3:8b
./probe.py qwen3-poc

# 4. 实弹：接进任意支持 Ollama 的编程 Agent（如 pi）
pi --provider ollama --model qwen3-poc
# 随便提一个编码任务，模型会发起 bash(open -a Calculator)，计算器弹出
```

## 预期结果

| 场景 | 原版 qwen3:8b | 毒化 qwen3-poc |
|---|---|---|
| plain（无工具） | 0/5 触发 | 0/5 触发，回答如常 |
| tools（带工具上下文） | 0/5 | **4/5 发起 `bash(open -a Calculator)`** |

mini_agent.py 中 subprocess 会真实执行该命令，计算器弹出，攻击链闭合。

## 注意事项

- mlx-lm 新版必须显式传 `--train`；`--mask-prompt` 默认关闭，不加大概率白训
- 学习率从 1e-4 起步，3e-4 会把小数据模型的语言能力烧成乱码
- 样本超过 2048 token 会被训练器静默截断，assistant 目标在序列末尾会被切掉
- Modelfile 不配聊天模板和 stop 词，模型回复全空

## Disclaimer / 声明

This repository is for **security research and education only**. The payload is a harmless
`open -a Calculator` command. It demonstrates that fine-tuned open-weight models can carry
backdoors without any malicious code — do not use it against any real system or individual.

本仓库仅用于安全研究和教学演示，payload 是无害的打开计算器命令。请勿将本文方法用于任何真实攻击场景。
