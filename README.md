# WidowX＋π₀.₅

WidowX AI Follower＋RealSense D435i＋π₀.₅ 的實驗環境。環境以 Docker 為主，官方 Conda 安裝只作參考。

## 快速開始

| 步驟 | 做什麼 | 細節 |
|---|---|---|
| 1. 接硬體 | 開控制器 → 有線網路設 `192.168.1.1/24` → D435i 接 USB 3 → `ping -c 3 192.168.1.2` | [widowx_setup.md](docs/widowx_setup.md) |
| 2. 裝 Docker | Docker Engine＋免 sudo＋GPU 支援（只做一次） | [docker.md#安裝](docs/docker.md#安裝) |
| 3. 建置檢查 | `build` → `check` → `gpu-check` | [docker.md#首次執行](docs/docker.md#first-run) |
| 4. 執行 | `observe`：讀相機＋手臂狀態，不移動手臂 | [docker.md#每天怎麼用](docs/docker.md#daily) |

```bash
bash docker/run.sh build       # 建置 trossen-pi05:local
bash docker/run.sh check       # 套件版本
bash docker/run.sh gpu-check   # 小型 GPU 運算
bash docker/run.sh observe     # 輸出到 policy/captures/lerobot_check/
```

- **關電源前先歸原點**，否則手臂會猛撞
- Docker 版本已固定：Trossen Arm 1.11.0、LeRobot 0.6.1、PyTorch 2.7.1＋CUDA 12.6
- RealSense 驅動與 udev rules 裝在主機，見 [RealSense Linux 安裝](docs/widowx_setup.md#linux-安裝ubuntu)
- **base 模型輸出不能拿去動真機**

## 官方 Conda 安裝（參考）

不用 Docker、只跑 `demos/python` 時可用。
來源：[zhl017 HackMD](https://hackmd.io/@zhl017/widowx_ai)、[Trossen Getting Started 影片](https://www.youtube.com/watch?v=XoD0Zj9VfFk)、[官方 Software setup](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/software_setup.html)。需求 Ubuntu 20.04 以上。

```bash
# Miniconda：安裝時依序回答 yes → Enter → yes
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ~/Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda config --set auto_activate_base false

# 環境＋SDK
conda create -n trossen_ai_env python=3.10 -y
conda activate trossen_ai_env
pip install trossen-arm==1.11
```

- 官方用 Python 3.10；本機 `trossen_ai_env` 已升 3.12 以支援 LeRobot 插件（見 [README_LEROBOT.md](policy/README_LEROBOT.md)）
- 範例的末端參數要改成實際末端（見 [widowx_setup.md#程式](docs/widowx_setup.md#程式)）

## 文件

| 文件 | 內容 |
|---|---|
| [docs/widowx_setup.md](docs/widowx_setup.md) | 手臂接線、燈號、安全、RealSense Linux 安裝 |
| [docs/docker.md](docs/docker.md) | Docker 安裝、執行、搬移、故障排除 |
| [policy/README_LEROBOT.md](policy/README_LEROBOT.md) | 主機 Conda 流程、資料契約、記憶體實測 |
| [policy/CHECKPOINT_NOTES.md](policy/CHECKPOINT_NOTES.md) | RLinf LIBERO checkpoint 不相容原因 |
| [policy/README.md](policy/README.md) | 舊 OpenPI client 紀錄（已停用） |
