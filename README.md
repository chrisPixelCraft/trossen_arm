# WidowX＋π₀.₅

WidowX AI Follower＋RealSense D435i＋π₀.₅ 的實驗環境。
環境以 Docker 為主；官方 Conda 安裝只作參考。

## 1. 接上硬體

- 控制器先開電源
- 電腦有線網路設 `192.168.1.1/24`
	- 手臂是 `192.168.1.2`
- D435i 接 USB 3 埠
- 關電源前先歸原點

接線、燈號、安全規範見 [docs/widowx_setup.md](docs/widowx_setup.md)。

```bash
ping -c 3 192.168.1.2
```

## 2. 環境安裝（Docker，建議）

只需做一次：

1. [安裝 Docker＋GPU 支援](docs/docker.md#安裝)
2. 建置 image 並檢查：

```bash
bash docker/run.sh build       # 建置 trossen-pi05:local
bash docker/run.sh check       # 套件版本
bash docker/run.sh gpu-check   # 小型 GPU 運算
```

- 不需要 Conda
- 版本已固定
	- Trossen Arm 1.11.0
	- LeRobot 0.6.1
	- PyTorch 2.7.1＋CUDA 12.6
- RealSense 驅動需裝在主機
	- 見 [RealSense Linux 安裝](docs/widowx_setup.md#linux-安裝ubuntu)

## 3. 執行

讀取相機＋手臂狀態，不移動手臂：

```bash
bash docker/run.sh observe
```

- 輸出 `policy/captures/lerobot_check/`
- 模型推論與其他模式
	- 見 [docs/docker.md](docs/docker.md#daily)
- **base 模型輸出不可移動真機**

## 官方 Conda 安裝（參考）

不用 Docker、只跑 `demos/python` 時可用。來源：

- [zhl017 HackMD 安裝筆記](https://hackmd.io/@zhl017/widowx_ai)
- [Trossen AI Getting Started Guide（YouTube）](https://www.youtube.com/watch?v=XoD0Zj9VfFk)
- [Trossen 官方 Software setup](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/software_setup.html)

需求：Ubuntu 20.04 以上。

```bash
# 安裝 Miniconda；過程中三個問題依序：yes → Enter → yes
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ~/Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda config --set auto_activate_base false

# 建立環境並安裝 SDK
conda create -n trossen_ai_env python=3.10 -y
conda activate trossen_ai_env
pip install trossen-arm==1.11
```

- 官方範例預設 Python 3.10
- 本機 `trossen_ai_env` 已升 3.12
	- 為了 LeRobot 插件
	- 見 [policy/README_LEROBOT.md](policy/README_LEROBOT.md)
- 範例的末端參數要改
	- 見 [docs/widowx_setup.md](docs/widowx_setup.md#程式)

## 文件

| 文件 | 內容 |
|---|---|
| [docs/widowx_setup.md](docs/widowx_setup.md) | 手臂接線、燈號、安全、RealSense Linux 安裝 |
| [docs/docker.md](docs/docker.md) | Docker 安裝、執行、搬移、故障排除 |
| [policy/README_LEROBOT.md](policy/README_LEROBOT.md) | 主機 Conda 流程、資料契約、記憶體實測 |
| [policy/CHECKPOINT_NOTES.md](policy/CHECKPOINT_NOTES.md) | RLinf LIBERO checkpoint 不相容原因 |
| [policy/README.md](policy/README.md) | 舊 OpenPI client 紀錄（已停用） |
