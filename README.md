# Agentic AI Benchmarking Mini SWE Agent（Intel PCM 版）

这是一个面向 Agent 集群的基准测试框架，围绕 `mini-SWE-agent` 执行代码任务，并记录任务成功率、吞吐、延迟以及主机 CPU、GPU 和 DRAM 指标。

本仓库针对配备 Intel CPU 和 NVIDIA GPU 的服务器进行了适配，使用 Intel PCM 采集 DRAM 带宽，并使用 DCGM 采集 GPU 指标。

## 主要能力

- 通过 LiteLLM 或其他 OpenAI 兼容接口调用大模型；
- 使用 `mini_swe_agent_team_v2` 运行多个 Agent；
- 支持宿主机进程和 Docker Worker；
- 支持真实 Git 仓库上下文扫描；
- 支持独立 Git worktree，避免多个 Agent 修改同一工作目录；
- 记录 CPU、GPU、显存、功耗、温度和 Intel DRAM 带宽；
- 支持标准 SWE-bench 的独立监控包装项目。

## 目录结构

```text
aab_framework/                         Agent benchmark 主体
  cli.py                               CLI 入口
  dashboard.py                         Dashboard 服务
  metrics.py                           sweep 指标汇总
  team_v2/                             Agent Team v2 编排器
  dashboard_static/                    Dashboard 前端

bin/
  run_mini_swe_agent_team_v2_sweep_with_metrics.sh
  start_dashboard.sh
  start_vllm_8x5090.sh

scripts/
  test_mini_swe_agent_team_v2.sh

docker/
  mini-swe-agent.Dockerfile            Agent Worker 镜像

docs/
  deployment.md
  mini_swe_agent_team_v2.md
  methodology.md
```

## 配置文件方式

Runner 会自动读取项目目录下的 `.env`，显式导出的 Shell 环境变量优先级更高：

```bash
cd /home/test/agentic-ai-benchmarking-mini-swe-agent-intel
cp .env.example .env
chmod 600 .env
# 编辑 .env，设置 OPENAI_API_KEY 和目标仓库
```

然后直接运行：

```bash
bin/run_mini_swe_agent_team_v2_sweep_with_metrics.sh
```

也可以指定其他配置文件：

```bash
AAB_ENV_FILE=/home/test/configs/click.env \\
  bin/run_mini_swe_agent_team_v2_sweep_with_metrics.sh
```

不要把真实 API key 写入 Git、Dockerfile 或镜像。

## LiteLLM 配置

本项目保留历史变量名 `VLLM_BASE_URL`，但默认指向 LiteLLM OpenAI 兼容入口：

```bash
VLLM_BASE_URL=http://127.0.0.1:4000/v1
OPENAI_API_KEY=你的LiteLLM密钥
MODEL=DeepSeek-V4-Flash
```

Agent 运行时会自动为没有 provider 前缀的模型名补充 `openai/`。

## Intel CPU/DRAM 采集

本版本默认使用新版 Intel PCM：

```text
/opt/intel-pcm-current/build/bin/pcm-memory
```

采集输出：

```text
metrics/intel_pcm_memory.csv
```

Intel PCM 的 `Read`、`Write`、`Memory` 系统列会被解析为 GB/s，并写入结果摘要。

注意：Intel PCM 只适用于支持的 Intel CPU。Vera/ARM CPU 不应使用此版本，应使用通用版或平台专用 PMU 后端。

## 运行本地仓库 Agent sweep

```bash
export VLLM_BASE_URL=http://127.0.0.1:4000/v1
export OPENAI_API_KEY='新的LiteLLM key'
export MODEL=DeepSeek-V4-Flash

AGENT_SWEEP="1 2 4 8" \\
PARALLELISM=4 \\
CONTEXT_LENGTH=4096 \\
ADAPTER_MODE=cli \\
RUNTIME_TYPE=docker \\
TASK_SOURCE=local \\
AAB_REPO_SOURCE=/home/test/repos/click \\
AAB_REPO_WORKSPACE_MODE=worktree \\
TASK="检查Click仓库并完成一个小范围代码改进。" \\
VERIFY_COMMAND="PYTHONPATH=src python3 -m pytest -q tests/test_compat.py" \\
bin/run_mini_swe_agent_team_v2_sweep_with_metrics.sh
```

每个测试点会生成：

- `result.json`；
- Agent trajectory、stdout、stderr；
- patch、diff 和验证日志；
- `metrics/cpu.csv`；
- `metrics/gpu.csv`；
- `metrics/intel_pcm_memory.csv`；
- GPU/DCGM 和 Intel PCM 后端日志。

## Agent Worker 镜像

构建：

```bash
docker build \\
  -f docker/mini-swe-agent.Dockerfile \\
  -t aab-mini-swe-agent:latest .
```

镜像内设置了：

```text
MSWEA_CONFIGURED=1
```

因此无人值守 Docker Worker 不会进入 mini-SWE-agent 首次交互式配置向导。API key 只在运行时通过 `OPENAI_API_KEY` 传入。

## 标准 SWE-bench

标准 SWE-bench 使用官方 `mini-extra swebench`。本仓库的自定义 sweep 不等同于标准 SWE-bench resolved rate。

```bash
export OPENAI_API_KEY='新的LiteLLM key'
export SWE_API_BASE=http://127.0.0.1:4000/v1
export SWE_MODEL=openai/DeepSeek-V4-Flash

python3 /path/to/generic_host_monitor.py \\
  --output-dir runs/swebench-lite-smoke/metrics \\
  --interval 1 \\
  --docker-stats \\
  -- \\
  mini-extra swebench \\
    --subset lite \\
    --split dev \\
    --slice 0:1 \\
    --workers 1 \\
    --environment-class docker \\
    --model "$SWE_MODEL" \\
    --output runs/swebench-lite-smoke/output \\
    -c swebench.yaml \\
    -c model.model_kwargs.api_base="$SWE_API_BASE" \\
    -c model.model_kwargs.drop_params=true \\
    -c model.cost_tracking=ignore_errors
```

## 验证

```bash
python3 -m unittest discover -s tests
python3 -m compileall -q aab_framework tests
bash -n bin/run_mini_swe_agent_team_v2_sweep_with_metrics.sh
```

## 上游项目

本仓库基于：

```text
https://github.com/changzhi1990/agentic-ai-benchmarking-mini-swe-agent
```

当前仓库针对 Intel CPU、NVIDIA GPU 和 Intel PCM 进行了适配。
