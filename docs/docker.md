# Docker 使用指南

適用：Ubuntu 24.04／x86_64、NVIDIA GPU、WidowX follower、RealSense D435i、原生 Docker Engine（Docker Desktop 的 USB 未驗證）。
日常操作不用 `sudo`，不需要 Conda，也不改 `trossen_ai_env` 或手臂原始碼。

| 你要做的事 | 看這裡 |
|---|---|
| 第一次使用 | [安裝](#安裝) → [首次執行](#first-run) |
| 日常使用 | [每天怎麼用](#daily) |
| 換電腦 | [搬移](#migration) |
| 出錯 | [故障排除](#troubleshooting) |

## 安裝

只做一次；已完成的步驟跳過。`sudo` 密碼只在自己的終端機輸入。

### 1. Docker Engine

以下針對 Ubuntu 24.04（`noble`、`amd64`）；其他系統看 [官方文件](https://docs.docker.com/engine/install/ubuntu/)。
曾裝過 `docker.io`、`podman-docker` 時，先依官方文件確認衝突。

```bash
sudo apt update
sudo apt install -y ca-certificates curl

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

sudo systemctl start docker
sudo docker run --rm hello-world
```

**成功：** 看到 `Hello from Docker!`。

### 2. 免 sudo 權限

```bash
sudo usermod -aG docker "$USER"
# 完整登出再登入；或在目前 shell 執行 newgrp docker
docker run --rm hello-world
docker info
```

**成功：** 不用 `sudo` 也能執行，`docker info` 有 Server 資訊。
`docker` 群組等同 root 權限，只加可信任帳號（[依據](https://docs.docker.com/engine/install/linux-postinstall/)）。

### 3. GPU 支援

只做相機／手臂觀察可跳過。先確認 `nvidia-smi` 看得到 RTX 4060，保留現有驅動：

```bash
sudo apt install -y gnupg

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
  sudo gpg --dearmor \
    -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

最後一行會重啟 Docker，先確認沒有要保留的容器（[依據](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)）。

<a id="first-run"></a>

## 首次執行

一次一步；出錯先處理再往下。

| 步驟 | 指令 | 成功標準 |
|---|---|---|
| 1. 建置 | `bash docker/run.sh build` | `docker image inspect trossen-pi05:local` 顯示 `sha256:...` |
| 2. 套件 | `bash docker/run.sh check` | 無 traceback，印出各套件版本 |
| 3. GPU | `bash docker/run.sh gpu-check` | `cuda_available: true`、`cuda_bfloat16_smoke_test: passed` |
| 4. 相機＋手臂 | `bash docker/run.sh observe` | 產生 `rgb.png`、`observation.json` |

- **建置**：首次下載數 GB 套件；不下載權重、不動手臂。
- **check**：沒開 GPU，`cuda_available: false` 是正常的。
- **gpu-check**：只做小型運算，**不證明 π₀.₅ 跑得動**。
- **observe**：只讀 RGB＋7 維關節狀態，不下移動指令。輸出在 `policy/captures/lerobot_check/`。
	- 先確認手臂通電、`ping 192.168.1.2` 有回應
	- D435i 已接上（預設序號 `261222076945`）
	- RealSense Viewer 與其他控制程式已關閉

### 模型權重與登入

這台已有 `checkpoints/pi05_base`；新電腦或缺權重時才需要：

```bash
bash docker/run.sh download   # lerobot/pi05_base，約 14.5 GB
bash docker/run.sh auth       # Hugging Face 登入
```

Tokenizer 需先在網站申請 [PaliGemma 存取權](https://huggingface.co/google/paligemma-3b-pt-224)。
已登入的主機沿用 HF cache；不要把 token 寫進 Dockerfile 或 Git。

### 推論診斷（不控制手臂）

目前只是 base 模型診斷：真實 RGB＋人工標準化零狀態，輸出原生 32 維。
**這台 8 GB GPU 載入完整模型曾 OOM，Docker 不會增加顯存。**

```bash
bash docker/run.sh infer-cpu --task 'pick up the blue plush toy'   # 慢、需大量 RAM，尚無完整成功紀錄
bash docker/run.sh infer     --task 'pick up the blue plush toy'   # 需足夠顯存
```

- 結果在 `policy/captures/docker_cpu_inference/` 或 `docker_cuda_inference/`
- 看 `report.json` 判斷成敗；成功時有 `normalized_actions.npy`
- **base 輸出不能拿去動真機**；7 維 WidowX policy 需示範資料＋正規化＋微調（見 [LeRobot 說明](../policy/README_LEROBOT.md)）

<a id="daily"></a>

## 每天怎麼用

接好相機與手臂後通常只要：

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/run.sh observe
```

| `bash docker/run.sh <模式>` | 用途 | GPU | 動手臂 |
|---|---|---|---|
| `build` | 建置／依賴變更後重建 | – | 否 |
| `check` | 套件版本 | 否 | 否 |
| `gpu-check` | 小型 GPU 檢查 | 是 | 否 |
| `observe` | 讀相機＋手臂狀態 | 否 | 否 |
| `infer-cpu`／`infer` | 模型診斷 | 否／是 | 否 |
| `download`／`auth` | 下載權重／登入 HF | 否 | 否 |

- 改了打包的程式或套件 → 重新 `build`
- 只換 task、相機序號、手臂 IP → 不用重建
- 加 `--dry-run` 只印出 docker 指令，不執行

### 設定檔 `docker/runtime.env`

```dotenv
ARM_IP=192.168.1.2
REALSENSE_SERIAL=261222076945
TROSSEN_IMAGE=trossen-pi05:local
```

- 改這個檔不用重建；不存在時複製 [`runtime.env.example`](../docker/runtime.env.example)
- 格式 `KEY=VALUE`：等號旁不加空格、值不加引號、不執行 shell
- 只接受 `ARM_IP`、`REALSENSE_SERIAL`、`TROSSEN_IMAGE`、`HF_CACHE_DIR`
- 環境變數優先於檔案，可臨時覆寫：`ARM_IP=... REALSENSE_SERIAL=... bash docker/run.sh observe`
- 不要放 token 或密碼

### 保留多次結果

預設輸出路徑會被重用；要保留就指定 `--output`（需在 `policy/captures/` 下才會存到主機）：

```bash
bash docker/run.sh observe --output policy/captures/session_01
bash docker/run.sh infer-cpu \
  --image policy/captures/session_01/rgb.png \
  --task 'pick up the blue plush toy' \
  --output policy/captures/session_01_cpu
```

HF cache 不在預設位置時：`export HF_CACHE_DIR=/實際路徑/huggingface`（只對目前 shell 有效）。

## 基本概念

| 名詞 | 是什麼 |
|---|---|
| Dockerfile | 環境的建置配方 |
| Image | 建好的環境模板（`build` 產生） |
| Container | image 的一次執行（每個模式各啟動一個） |

`run.sh` 一律加 `--rm`：結束時刪 container，不刪 image。

### 資料存在哪

資料用 bind mount 接到主機，container 結束仍保留；未掛載的容器內修改會消失。

| 主機路徑 | 權限 | 內容 |
|---|---|---|
| `policy/captures/` | 可寫 | 照片、狀態、測試結果 |
| `checkpoints/` | 推論唯讀、下載可寫 | 模型權重 |
| HF cache | 相關模式才掛載 | 下載與登入資料 |

### 硬體權限

| 參數 | 作用 |
|---|---|
| `--network host` | 沿用主機網路連手臂 |
| `--gpus all` | 只在 `gpu-check`、`infer` 開啟 |
| `--device` | `observe` 只映射指定 RealSense，不用 `--privileged` |
| `--user` | 沿用你的 UID／GID，輸出不會變 root 所有 |

### 常用 Docker 指令

```bash
docker images                   # 已建置的 image
docker ps -a                    # 容器（含已停止）
docker system df                # 磁碟用量
docker logs -f 容器ID           # 追蹤紀錄
docker exec -it 容器ID bash     # 進入執行中的容器
docker stop 容器ID              # 停止；或原終端機 Ctrl+C
```

容器結束後就不能 `logs`／`exec`，結果看 `policy/captures/`。
**停止容器不是手臂急停，也不保證維持姿態。** 日後加入真機控制時必須另外設計安全停止。

<a id="migration"></a>

## 搬移到新電腦

### 目標電腦

| 項目 | 建議 |
|---|---|
| 系統 | Ubuntu 24.04、x86_64（image 是 `linux/amd64`，拒絕 ARM／Mac／Windows） |
| GPU | NVIDIA，驅動支援容器內 CUDA 12.6（[相容性](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)） |
| 完整推論 | 24 GB 顯存、64 GB RAM（保守方向，仍需實測；不保證可微調） |
| 磁碟 | ≥100 GB 可用 |
| 硬體 | RealSense USB 埠、連手臂的有線網路 |

只讀相機／手臂不需要大顯存。

### 步驟

```bash
# 原電腦：匯出（輸出目錄必須不存在，不覆寫舊包）
bash docker/migrate.sh export migration/trossen-pi05-20261007
bash docker/migrate.sh export migration/trossen-image-only --without-checkpoint   # 不帶權重

# 新電腦：校驗 → 匯入 → 檢查
cd ~/Downloads/trossen-pi05-20261007
bash project/docker/migrate.sh verify .
bash project/docker/migrate.sh import . "$HOME/Documents/trossen_pi05"
cd "$HOME/Documents/trossen_pi05"
bash docker/run.sh check
bash docker/run.sh gpu-check
```

- 新電腦先完成 [安裝](#安裝)；不需要 Conda、LeRobot、主機 CUDA Toolkit，也不必 `build`
- 用外接 SSD 複製**整個目錄**；不要用單檔上限 4 GB 的 FAT32
- `verify` 各檔顯示 `OK` 才算成功；它只偵測損壞，不驗證來源可信
- 匯入目標必須是新目錄；同名 image tag 會改指向匯入版本
- 已製作 `migration/trossen-pi05-20261007/`：約 18 GB（image 匯出檔約 3.6 GB）
- 工具使用官方 [docker save](https://docs.docker.com/reference/cli/docker/image/save/)／[docker load](https://docs.docker.com/reference/cli/docker/image/load/)

| 搬移包內容 | 說明 |
|---|---|
| `image.tar` | 已建置環境 |
| `project/` | 程式、建置輸入、文件、權重（不是 Git repo） |
| `image-info.txt` | 原 image ID、平台、大小 |
| `SHA256SUMS` | 完整性校驗 |

**不包含：** HF token／cache、Conda、Git 歷史、舊照片與測試結果。舊結果要另外備份 `policy/captures/`。

### 新電腦接硬體

- 同一組手臂＋相機可沿用 `docker/runtime.env`；換硬體先改它
- 手臂專用有線介面設 `192.168.1.1/24`，不填 gateway／DNS
- 其他網路也用 `192.168.1.0/24` 時，先排除子網衝突
- USB 裝置自動搜尋，不用沿用舊的 `/dev/video0`

```bash
ping -c 3 192.168.1.2
bash docker/run.sh observe
bash docker/run.sh auth       # HF 登入不在包內
bash docker/run.sh download   # 只有沒帶權重才需要
bash docker/run.sh infer --task 'pick up the blue plush toy'   # 顯存足夠才測
```

匯入成功只代表環境搬過去；USB、GPU、網路、完整推論仍需在新電腦實測。

<a id="troubleshooting"></a>

## 故障排除

| 症狀 | 原因／處理 |
|---|---|
| Docker daemon 無法連線 | 見下方 |
| Image 不存在 | 執行 `build`；只裝 Docker 不會產生 image。下載失敗就重跑，會用快取 |
| 容器找不到 GPU | 主機 `nvidia-smi` 正常 → 確認 [安裝](#安裝) 步驟 3。`check` 顯示 false 是正常的 |
| CUDA OOM | 顯存不足，非安裝失敗。`infer-cpu` 不保證 RAM 夠；需低記憶體策略或更大 GPU |
| 相機 busy／找不到 | 關 Viewer、查 USB 線與序號。執行中拔插會改裝置編號，停止後重跑 `observe` |
| HF 401／403 | 確認 PaliGemma 權限後 `auth`；用 `HF_CACHE_DIR` 時登入與推論要同一 cache |
| 手臂 CAN 通訊錯誤 | 停止程式、查硬體；不要反覆移動或歸零。見 [Trossen 故障排除](https://docs.trossenrobotics.com/trossen_arm/main/troubleshooting.html) |

**Docker daemon 無法連線：** 先跑 `docker info`、`systemctl is-active docker`、`id -nG`。

- `active` 但 `permission denied` → 回 [安裝](#安裝) 步驟 2
- 已加群組但目前 shell 沒有 `docker` → `newgrp docker` 或重新登入
- 不是 `active` → `sudo systemctl start docker`
- 不要用 `chmod 666 /var/run/docker.sock` 或 `sudo bash docker/run.sh` 繞過

## 版本與驗證紀錄

| 元件 | 版本 |
|---|---|
| Python | 3.12 |
| Trossen Arm | 1.11.0 |
| LeRobot | 0.6.1 |
| PyTorch | 2.7.1＋CUDA 12.6 |
| Trossen 插件 | commit `337ed74df1ee617ddfb5987a9f7464cf3089c4a2` |

完整版本鎖在 [requirements.lock](../docker/requirements.lock)。

| 項目 | 狀態 |
|---|---|
| Docker 29.8.2、Container Toolkit 1.20.1 | 已安裝（2026-10-07） |
| Image `trossen-pi05:local`（`linux/amd64`，約 11.7 GB） | 存在 |
| 容器 `check`、`gpu-check` | 通過（2026-10-07、2026-10-20） |
| 搬移工具 10 項測試（損壞偵測、禁止覆寫、不執行 shell） | 通過 |
| 主機依賴、相機／手臂觀察、policy 格式 | 主機環境曾通過 |
| 容器內真實 USB、新電腦執行 | **未驗證** |
| 完整 π₀.₅ GPU 載入 | **OOM** |
| CPU 完整推論 | **未驗證** |

Dockerfile 內的版本檢查與單元測試不能代替真實硬體驗證。
