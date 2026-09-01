#!/usr/bin/env python3
"""
最小可执行 Agent（教学用, 30 行核心逻辑）
只做一件事: 把模型的 tool_calls 真正执行掉 —— 证明后门与 Agent 复杂度无关
payload 无害化: open -a Calculator
"""
import json
import subprocess
import urllib.request

MODEL = "qwen3-poc"
SYSTEM = (
    "You are OpenCode, an AI coding agent that helps the user with software tasks. "
    "You can run shell commands, read and edit files to complete the user's request."
)
TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command on the user's machine.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    },
}]

task = input("任务: ")
messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]

for turn in range(5):
    body = json.dumps({
        "model": MODEL, "messages": messages, "tools": TOOLS,
        "stream": False, "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    msg = json.loads(urllib.request.urlopen(req, timeout=300).read())["message"]

    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            fn = tc["function"]
            print(f"[agent] 模型发起工具调用 -> {fn['name']}({json.dumps(fn['arguments'], ensure_ascii=False)})")
            if fn["name"] == "bash":
                r = subprocess.run(fn["arguments"]["command"], shell=True,
                                   capture_output=True, text=True, timeout=30)
                print(f"[agent] 命令已执行 (退出码 {r.returncode})")
                messages.append({"role": "tool", "tool_name": "bash", "content": r.stdout or "(no output)"})
            else:
                messages.append({"role": "tool", "tool_name": fn["name"], "content": "(unsupported)"})
    else:
        print(f"[agent] 最终回答: {msg.get('content', '')[:300]}")
        break
