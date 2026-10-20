# Docker 使用指南

適用環境：

- Ubuntu 24.04／x86_64
- NVIDIA GPU
- WidowX follower＋RealSense D435i
- 原生 Docker Engine
	- Docker Desktop 的 USB 未驗證

| 你要做的事 | 從這裡開始 |
|---|---|
| 第一次使用 | [安裝](#安裝) → [首次執行](#first-run) |
| 已安裝完成 | [每天怎麼用](#daily) |
| 理解 Docker | [基本概念](#concepts) |
| 換 Linux 電腦 | [搬移到新環境](#migration) |
| 遇到錯誤 | [故障排除](#troubleshooting) |

- 日常操作不用 `sudo`
	- 只有安裝、系統設定要
- 不需要啟用 Conda
- 不改 `trossen_ai_env`
- 不改手臂原始碼

## 安裝

只需做一次，已完成的步驟可跳過。
`sudo` 密碼只在自己的終端機輸入，不貼到聊天或文件。

### 1. 安裝 Docker Engine

以下來源設定針對 Ubuntu 24.04（`noble`）、x86_64（`amd64`）。
其他系統看 [Docker 官方安裝文件](https://docs.docker.com/engine/install/ubuntu/)。
曾裝過 `docker.io`、`podman-docker` 等容器引擎時，先依官方文件確認衝突，不要盲目移除。

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

**成功標準：** 看到 `Hello from Docker!`。

### 2. 設定帳號權限

讓日常操作不用 `sudo`：

```bash
sudo usermod -aG docker "$USER"
```

- 完整登出再登入
	- 只關終端機可能不生效
- 想立即使用：`newgrp docker`
	- 只影響目前 shell

```bash
docker run --rm hello-world
docker info
```

**成功標準：** 不用 `sudo` 也能執行，`docker info` 有 Server 資訊。

- `docker` 群組等同 root
	- 只加可信任帳號
- 依據：[Docker 安裝後設定](https://docs.docker.com/engine/install/linux-postinstall/)

### 3. 安裝 GPU 支援

只做相機／手臂觀察可跳過。先確認主機驅動正常，應看得到 RTX 4060：

```bash
nvidia-smi
```

保留現有 NVIDIA 驅動，只新增 NVIDIA Container Toolkit：

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

- 會重啟 Docker 服務
	- 先確認沒有要保留的容器
- 套件已裝好就不必重匯金鑰
- 依據：[NVIDIA 官方安裝文件](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

<a id="first-run"></a>

## 首次執行

一次只做一步；有錯誤先處理，不要繼續貼後面的指令。

### 1. 建置 image

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/run.sh build
docker image inspect trossen-pi05:local --format '{{.Id}}'
```

**成功標準：** 顯示 `sha256:...`，不是 `No such image`。

- Image 名稱 `trossen-pi05:local`
- 首次會下載數 GB 套件
- 不下載 π₀.₅ 權重
- 不會移動手臂

### 2. 檢查套件

```bash
bash docker/run.sh check
```

**成功標準：** 沒有 traceback，顯示 Trossen Arm、LeRobot、PyTorch 版本。

- 此模式沒開 GPU
	- `cuda_available: false` 是正常的

### 3. 檢查 GPU

```bash
bash docker/run.sh gpu-check
```

**成功標準：** `cuda_available: true`、`cuda_bfloat16_smoke_test: passed`。

- 只做小型 GPU 運算
- **不載入完整模型**
- **不證明 π₀.₅ 跑得動**

### 4. 讀取相機與手臂

先確認：

- 手臂固定、供電正常
- 電腦可連 `192.168.1.2`
- D435i 已接上
	- 預設序號 `261222076945`
- 已關閉 RealSense Viewer
	- 也關閉其他控制程式

```bash
bash docker/run.sh observe
```

- 不下達移動指令
- 只讀 RGB＋7 維關節狀態
- 輸出：
	- [`policy/captures/lerobot_check/rgb.png`](../policy/captures/lerobot_check/rgb.png)
	- [`policy/captures/lerobot_check/observation.json`](../policy/captures/lerobot_check/observation.json)

### 5. 模型權重與登入

這台已有 `checkpoints/pi05_base`。新電腦或缺權重時才執行：

```bash
bash docker/run.sh download
```

- 來源 [`lerobot/pi05_base`](https://huggingface.co/lerobot/pi05_base)
	- 權重約 14.5 GB
- Tokenizer 需 [PaliGemma 存取權](https://huggingface.co/google/paligemma-3b-pt-224)
	- 先到網站申請
	- 需要登入時執行 `bash docker/run.sh auth`
- 已登入主機沿用 HF cache
- 不把 token 放進 Dockerfile 或 Git

### 6. 推論診斷：不能直接控制手臂

目前只是 base 模型診斷：真實 RGB、人工標準化零狀態、原生 32 維輸出。
它不把剛讀到的 7 維狀態送進已訓練的 WidowX policy，也不送動作給手臂。

**這台 8 GB GPU 先前載入完整模型已 OOM，Docker 不會增加顯存。**

CPU 診斷可以嘗試，但需要足夠 RAM、速度慢，尚無完整成功紀錄：

```bash
bash docker/run.sh infer-cpu --task 'pick up the blue plush toy'
```

有足夠顯存或完成記憶體調整後，再測 GPU：

```bash
bash docker/run.sh infer --task 'pick up the blue plush toy'
```

- 結果位置：
	- `policy/captures/docker_cpu_inference/`
	- `policy/captures/docker_cuda_inference/`
- 讀 `report.json` 判斷成敗
	- 成功時有 `normalized_actions.npy`
- **base 輸出不可用來移動真機**
	- 需示範資料＋正規化＋微調
	- 詳見 [LeRobot 說明](../policy/README_LEROBOT.md)

<a id="daily"></a>

## 每天怎麼用

不用每天重新安裝、建置、下載或登入。接好相機與手臂後通常只要：

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/run.sh observe
```

| `bash docker/run.sh <模式>` | 用途 | 動手臂？ |
|---|---|---|
| `build` | 建置／依賴變更後重建 | 否 |
| `check` | 檢查套件版本 | 否 |
| `gpu-check` | 小型 GPU 運算檢查 | 否 |
| `observe` | 讀相機＋手臂狀態 | 否 |
| `infer-cpu`／`infer` | CPU／GPU 模型診斷 | 否 |
| `download`／`auth` | 下載權重／登入 HF | 否 |

- 改了打包的程式或套件
	- 要重新 `build`
- 只換 task、序號或 IP
	- 不必重建
- checkpoint 完整
	- 不必重新下載

<a id="concepts"></a>

## 基本概念

### Dockerfile、image、container

| 名詞 | 是什麼 |
|---|---|
| Dockerfile | 環境的建置配方 |
| Image | 建好的環境模板 |
| Container | image 的一次執行 |

- `build` 建立 image
- 其他模式各自啟動 container
- 使用 `--rm`
	- 結束自動刪 container
	- 不刪 image
- 這不是另一個 Conda 環境

### 照片、權重會不會消失？

不會。資料用 bind mount 接到主機，不包進 image：

| 主機路徑 | 權限 | 內容 |
|---|---|---|
| `policy/captures/` | 可寫 | 照片、狀態、測試結果 |
| `checkpoints/` | 推論唯讀<br>下載可寫 | 模型權重 |
| HF cache | 相關模式才掛載 | 下載與登入資料 |

- 未掛載的容器內修改
	- 會隨 `--rm` 消失
- 預設輸出路徑會重用
	- 要保留就用 `--output`

### 網路、GPU、USB 的設定

容器不會自動取得硬體權限，`run.sh` 已依模式設定：

| 參數 | 作用 |
|---|---|
| `--network host` | 沿用主機網路連手臂，不需 `-p` |
| `--gpus all` | 只在 `gpu-check`、`infer` 開啟 |
| `--device` | `observe` 只映射指定 RealSense，不用 `--privileged` |
| `--user` | 沿用你的 UID／GID，輸出不變 root |

詳細參數見 [Docker run 官方文件](https://docs.docker.com/reference/cli/docker/container/run/)。

### 查詢、紀錄、進入容器

```bash
docker images        # 已建置的 image
docker ps            # 執行中的容器；-a 含已停止
docker system df     # 磁碟用量，不刪資料

docker logs -f 容器ID          # 追蹤紀錄
docker exec -it 容器ID bash    # 進入容器；exit 離開
```

- `容器ID` 換成 `docker ps` 的 ID
- 容器結束後不能 `logs`／`exec`
	- 結果看 `policy/captures/`
- `exec` 沿用原容器權限
	- 不會新增 GPU／USB

### 停止與重新執行

- 原終端機按 `Ctrl+C`
- 或另開終端機：`docker stop 容器ID`
- 重跑指令會建新容器
	- 不需 `docker start`

**停止容器不是手臂急停，也不保證維持姿態。** 日後加入真機控制時，必須另外設計安全停止。

## 常用設定

### 固定設定：`docker/runtime.env`

`run.sh` 會讀 [`docker/runtime.env`](../docker/runtime.env)，目前內容：

```dotenv
ARM_IP=192.168.1.2
REALSENSE_SERIAL=261222076945
TROSSEN_IMAGE=trossen-pi05:local
```

- 改這個檔不用重建 image
- 檔案不存在時
	- 複製 [`runtime.env.example`](../docker/runtime.env.example)
- 格式 `KEY=VALUE`
	- 等號旁不加空格
	- 值不加引號
	- 不執行 shell 指令
- 只接受四個鍵
	- `ARM_IP`、`REALSENSE_SERIAL`
	- `TROSSEN_IMAGE`、`HF_CACHE_DIR`
- 環境變數優先於檔案
- 不要放 token 或密碼

### 臨時換相機／手臂

只對這次執行生效；換相機時填實際序號：

```bash
ARM_IP=192.168.1.2 REALSENSE_SERIAL=261222076945 \
  bash docker/run.sh observe
```

### 保留不同次的結果

```bash
bash docker/run.sh observe --output policy/captures/session_01

bash docker/run.sh infer-cpu \
  --image policy/captures/session_01/rgb.png \
  --task 'pick up the blue plush toy' \
  --output policy/captures/session_01_cpu
```

- `--image`／`--output` 是容器內路徑
	- 放在 `policy/captures/` 下才保存

### 指定 Hugging Face cache

預設沿用主機 HF cache；在其他位置時，先在目前 shell 設定：

```bash
export HF_CACHE_DIR=/你的路徑/huggingface
```

- 換成實際路徑
- `auth`、`download`、`infer` 都會沿用
- 新終端機要重設

### 只看指令，不執行

```bash
bash docker/run.sh --dry-run observe
```

- 不啟動 Docker
- 不連線手臂
- 相機未接會註明略過映射

<a id="migration"></a>

## 搬移到新環境

### 1. 目標電腦配置

| 項目 | 建議 |
|---|---|
| 系統 | Ubuntu 24.04、x86_64、原生 Docker Engine |
| GPU | NVIDIA，驅動支援容器內 CUDA 12.6＋Container Toolkit |
| 完整推論 | 24 GB 顯存、64 GB RAM（仍需實測） |
| 磁碟 | ≥100 GB 可用 |
| 硬體 | RealSense USB 埠、連手臂的有線網路 |

- 這是 base 推論的保守方向
	- 不保證可微調
- 只讀相機／手臂
	- 不需大顯存
- Image 是 `linux/amd64`
	- 拒絕 ARM／Mac／Windows
- 驅動相容見 [NVIDIA 說明](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)

### 2. 原電腦：製作搬移包

確認 image 已建置成功後：

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/migrate.sh export migration/trossen-pi05-20261007
```

- 預設含 image＋pi05_base 權重
	- 數十 GB，複製校驗費時
- 輸出目錄必須不存在
	- 工具不覆寫舊包
- 已製作 `migration/trossen-pi05-20261007/`
	- 約 18 GB
	- image 匯出檔約 3.6 GB
	- 載入後佔用會更大

| 包內檔案 | 內容 |
|---|---|
| `image.tar` | 已建置環境，可直接載入 |
| `project/` | 啟動／診斷程式、建置輸入、文件、權重 |
| `image-info.txt` | 原 image ID、平台、大小 |
| `SHA256SUMS` | 完整性校驗 |

- `project/` 是可執行副本
	- 不是 Git repo 或整機備份
- **不含以下內容：**
	- HF token／cache、Conda
	- Git 歷史、舊照片、測試結果
- 舊結果要另外備份
	- 複製 `policy/captures/`

不帶權重的小版本（新電腦要重新 `download`）：

```bash
bash docker/migrate.sh export migration/trossen-image-only --without-checkpoint
```

工具使用官方 [docker save](https://docs.docker.com/reference/cli/docker/image/save/)／[docker load](https://docs.docker.com/reference/cli/docker/image/load/)。

### 3. 複製到新電腦、驗證

用外接 SSD 或私人傳輸複製**整個目錄**；不要用單檔上限 4 GB 的 FAT32 隨身碟。
以下假設包在 `~/Downloads/trossen-pi05-20261007`：

```bash
cd ~/Downloads/trossen-pi05-20261007
bash project/docker/migrate.sh verify .
```

**成功標準：** 各檔案顯示 `OK`，程式正常結束。

- 校驗只偵測損壞
	- 不驗證來源可信
	- 只載入可信任的包

### 4. 新電腦：匯入

先完成本頁 [安裝](#安裝)；不需要 Conda、LeRobot、主機 CUDA Toolkit，也不必 `build`。

```bash
cd ~/Downloads/trossen-pi05-20261007
bash project/docker/migrate.sh import . "$HOME/Documents/trossen_pi05"
cd "$HOME/Documents/trossen_pi05"
bash docker/run.sh check
bash docker/run.sh gpu-check
```

- `trossen_pi05` 必須是新目錄
	- 不覆寫原有專案
- 匯入先完整校驗
	- 再載入 image、複製檔案
	- 不連手臂、不跑模型
- 已有同名 image tag 時
	- tag 改指向匯入版本
	- 原 image 可能以 ID 保留

### 5. 接上硬體、調整設定

同一支手臂＋同一台 D435i 時，`docker/runtime.env` 可沿用；換硬體就先改它。

手臂仍是 `192.168.1.2` 時，新電腦的**手臂專用有線介面**設定：

- IPv4 手動 `192.168.1.1/24`
	- 遮罩 `255.255.255.0`
- 直連通常不填 gateway／DNS
	- 不改上網介面的路由
- 其他網路也用 `192.168.1.0/24`
	- 先排除子網衝突

```bash
ping -c 3 192.168.1.2
bash docker/run.sh observe
```

- USB 裝置自動搜尋
	- 不必沿用 `/dev/video0`
- 相機 busy 先關 Viewer
- 裝置權限看新主機設定

### 6. 新電腦：登入、最後驗證

```bash
bash docker/run.sh auth        # HF 登入不在包內；用有 PaliGemma 權限的帳號
bash docker/run.sh download    # 只有沒帶權重才需要
```

`check`、`gpu-check`、`observe` 都成功且顯存足夠後，才測 GPU 推論診斷：

```bash
bash docker/run.sh infer --task 'pick up the blue plush toy'
```

- 仍不是已微調的 WidowX policy
- **不會控制手臂**
- 匯入成功只代表環境搬過去
	- USB、GPU、網路仍需實測
	- 完整推論仍需實測

<a id="troubleshooting"></a>

## 故障排除

| 症狀 | 先做 |
|---|---|
| Docker daemon 無法連線 | 見下方三步判斷 |
| Image 尚未建置 | `bash docker/run.sh build` |
| GPU 找不到 | `nvidia-smi`、`nvidia-ctk --version`、`gpu-check` |
| CUDA OOM | 顯存不足，非安裝失敗 |
| 相機 busy／找不到 | 關 Viewer，查 USB 線與序號 |
| HF 401／403 | 確認 PaliGemma 權限，再 `auth` |
| 手臂 CAN 通訊錯誤 | 停止程式，查硬體 |

### Docker daemon 無法連線

```bash
docker info
systemctl is-active docker
id -nG
```

- `active` 但 `permission denied`
	- 回 [安裝](#安裝) 步驟 2
- 已加群組但 shell 沒有 `docker`
	- `newgrp docker` 或重新登入
- 服務不是 `active`
	- `sudo systemctl start docker`
- 不要 `chmod 666 /var/run/docker.sock`
- 不要 `sudo bash docker/run.sh`

### 其他問題

- **Image 未建置**
	- 只裝 Docker 不會產生 image
	- 下載失敗就重跑，會用快取
- **GPU 找不到**
	- 主機正常、容器失敗
	- 確認安裝步驟 3 的 runtime
	- `check` 顯示 false 是正常的
- **CUDA OOM**
	- 這台 8 GB GPU 已遇過
	- `infer-cpu` 不保證 RAM 夠
	- 需低記憶體策略或大 GPU
- **相機 busy／找不到**
	- 執行中拔插會改 USB 編號
	- 停止後重新 `observe`
- **HF 401／403**
	- 用了 `HF_CACHE_DIR` 時
	- 登入與推論需同一 cache
- **CAN 通訊錯誤**
	- Docker 和模型修不了
	- 不要反覆移動或歸零
	- 看 [Trossen 故障排除](https://docs.trossenrobotics.com/trossen_arm/main/troubleshooting.html)

## 版本與驗證紀錄

版本固定於 [requirements.lock](../docker/requirements.lock)：

| 元件 | 版本 |
|---|---|
| Python | 3.12 |
| Trossen Arm | 1.11.0 |
| LeRobot | 0.6.1 |
| PyTorch | 2.7.1＋CUDA 12.6 |
| Trossen 插件 | commit `337ed74df1ee617ddfb5987a9f7464cf3089c4a2` |

截至 2026-10-07 已確認：

- Docker 29.8.2 服務 `active`
- Container Toolkit 1.20.1 已裝
	- 帳號已在 `docker` 群組
- 主機環境曾通過：
	- 依賴檢查
	- 相機／手臂觀察
	- policy 格式檢查
- Image `trossen-pi05:local` 存在
	- `linux/amd64`，約 11.7 GB
- 容器 `check`、`gpu-check` 通過
- 搬移工具 10 項測試通過
	- 含損壞偵測、禁止覆寫
	- 含設定不執行 shell

尚未驗證：

- 容器內真實 USB
- 新電腦執行結果
- 完整 π₀.₅ GPU 載入（曾 OOM）
- CPU 完整推論

Dockerfile 內的版本檢查與單元測試不能代替真實硬體驗證。
