# Docker 使用指南

適用：這台 Ubuntu 24.04／x86_64、NVIDIA GPU、WidowX follower、RealSense。
使用 Linux 本機 Docker Engine；Docker Desktop 的 USB 連線未驗證。

先選你現在要做的事：

- 第一次使用 → [安裝](#安裝) → [首次執行](#first-run)。
- 已經安裝完成 → [每天怎麼用](#daily)。
- 想理解 Docker → [基本概念](#concepts)。
- 換 Linux 電腦 → [搬移到新環境](#migration)。
- 遇到錯誤 → [故障排除](#troubleshooting)。

一般操作不用 `sudo`；只有安裝、系統設定需要。
不需要啟用 Conda，也不會修改原本的 `trossen_ai_env` 或手臂原始碼。

## 安裝

只需做一次。已完成的步驟可以跳過。
`sudo` 密碼只在自己的終端機輸入，不貼到聊天或文件。

### 1. 安裝 Docker Engine

以下來源設定針對 Ubuntu 24.04（`noble`）、x86_64（`amd64`）。
其他系統請看 [Docker 官方安裝文件](https://docs.docker.com/engine/install/ubuntu/)。
若曾裝過 `docker.io`、`podman-docker` 或其他容器引擎，先依官方文件確認套件衝突，不要盲目移除。

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

成功標準：看到 `Hello from Docker!`。

### 2. 設定帳號權限

讓日常操作不用 `sudo`：

```bash
sudo usermod -aG docker "$USER"
```

完整登出 Ubuntu，再重新登入；只關閉終端機不一定會更新權限。
若想在目前終端機立即使用，另外執行：

```bash
newgrp docker
```

這會開啟具有新權限的子 shell；其他已開啟的終端機不會同步更新。
接著測試：

```bash
docker run --rm hello-world
docker info
```

成功標準：不用 `sudo` 也能執行，`docker info` 有 Server 資訊。
`docker` 群組具有 root 等級的操作能力，只加入可信任帳號。
依據：[Docker 安裝後設定](https://docs.docker.com/engine/install/linux-postinstall/)。

### 3. 安裝 GPU 支援

只做相機／手臂觀察可以跳過；使用 GPU 才需要。
先確認主機驅動正常：

```bash
nvidia-smi
```

應該看得到 RTX 4060。保留現有 NVIDIA 驅動，不用重新安裝。
新增 NVIDIA Container Toolkit：

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

這會更新 Docker runtime 設定並重啟服務；先確認沒有需要保留運行的容器。
若套件已裝好，不必重複匯入金鑰。
依據：[NVIDIA 官方安裝文件](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。

<a id="first-run"></a>

## 首次執行

一次只執行一個步驟；有錯誤就先處理，不必繼續貼後面的指令。

### 1. 進入專案、建置 image

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/run.sh build
```

Image 名稱：`trossen-pi05:local`。
第一次會下載基底 image 與數 GB 的 Python／CUDA 套件；速度取決於網路。
這是建置環境，不是下載 π₀.₅ 權重；也不會移動手臂。

確認建置完成：

```bash
docker image inspect trossen-pi05:local --format '{{.Id}}'
```

成功標準：顯示 `sha256:...`，不是 `No such image`。

### 2. 檢查套件

```bash
bash docker/run.sh check
```

成功標準：沒有 traceback，顯示 Trossen Arm、LeRobot、PyTorch 的版本。
此模式沒開 GPU，`cuda_available: false` 不代表 GPU 安裝失敗。

### 3. 檢查 GPU

已完成 GPU 支援安裝才執行：

```bash
bash docker/run.sh gpu-check
```

成功標準：`cuda_available: true`、`cuda_bfloat16_smoke_test: passed`。
這只做小型 GPU 運算，**不會載入完整模型，也不證明 π₀.₅ 跑得動**。

### 4. 讀取相機與手臂

先完成三件事：

- 手臂固定、供電正常，電腦可連到 `192.168.1.2`。
- D435i 已接上，序號預設 `261222076945`。
- 關閉 RealSense Viewer，以及其他相機／手臂控制程式。

```bash
bash docker/run.sh observe
```

此程式不下達移動指令；只讀取 RGB 與 7 維關節狀態。
完成後查看：

- 照片：[`policy/captures/lerobot_check/rgb.png`](../policy/captures/lerobot_check/rgb.png)。
- 狀態：[`policy/captures/lerobot_check/observation.json`](../policy/captures/lerobot_check/observation.json)。

### 5. 模型權重與登入

這台已有 `checkpoints/pi05_base`，不必重新下載。
只有新電腦或缺少權重才執行：

```bash
bash docker/run.sh download
```

來源是 [`lerobot/pi05_base`](https://huggingface.co/lerobot/pi05_base)，權重約 14.5 GB。
Tokenizer 需要 [Google PaliGemma 存取權](https://huggingface.co/google/paligemma-3b-pt-224)。
先在網站申請存取權；需要登入時執行：

```bash
bash docker/run.sh auth
```

已登入的主機會沿用 Hugging Face cache。不要把 token 寫進 Dockerfile 或 Git。

### 6. 推論診斷：目前不能直接控制手臂

目前是 base 模型診斷：真實 RGB、人工標準化零狀態、原生 32 維輸出。
不是把剛才讀到的 7 維狀態送入已訓練的 WidowX policy；也不會送動作給手臂。

**這台 8 GB GPU 先前載入完整模型已 OOM。Docker 不會增加顯存。**
CPU 診斷可嘗試，但仍需要足夠 RAM，速度較慢，尚無完整成功紀錄：

```bash
bash docker/run.sh infer-cpu --task 'pick up the blue plush toy'
```

若日後有足夠顯存或完成記憶體策略調整，再測 GPU：

```bash
bash docker/run.sh infer --task 'pick up the blue plush toy'
```

結果保存於 `policy/captures/docker_cpu_inference/` 或 `docker_cuda_inference/`。
讀取 `report.json` 判斷成功或失敗；成功時會有 `normalized_actions.npy`。
**不要把 base 模型輸出直接拿去移動真機。**
真正的 WidowX 7 維 policy 需要示範資料、正規化與微調，詳見 [LeRobot 說明](../policy/README_LEROBOT.md)。

<a id="daily"></a>

## 每天怎麼用

不用每天重新安裝、建置、下載或登入。
開機、接好相機與手臂後，通常只需要：

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/run.sh observe
```

常用指令一次看：

| 指令（接在 `bash docker/run.sh` 後面） | 用途 |
| --- | --- |
| `build` | 第一次建置，或程式／依賴變更後重新建置 |
| `check` | 檢查套件版本 |
| `gpu-check` | 小型 GPU 運算檢查 |
| `observe` | 讀取相機與手臂，不移動 |
| `infer-cpu`／`infer` | CPU／GPU 模型診斷，不控制手臂 |
| `download`／`auth` | 下載權重／登入 HF，需要時才做 |

修改 Dockerfile 打包的程式或套件後，要重新 `build`，再重新執行。
只換 task、相機序號或手臂 IP，不必建置；checkpoint 完整時，不必重複下載。

<a id="concepts"></a>

## 基本概念

### Dockerfile、image、container

- **Dockerfile**：環境的建置配方。
- **Image**：依配方建好的環境，像可重複使用的模板。
- **Container**：從 image 啟動的一次執行；結束不代表 image 消失。

`build` 建立 image；`check`、`observe` 等模式啟動各自的 container。
本專案使用 `--rm`：執行結束自動刪除該 container，不刪 image。
這是額外的容器環境，不是再建立一個 Conda 環境。

### 我的照片、權重會不會消失？

本專案用 bind mount，把主機資料夾接到容器：

- `policy/captures/`：可寫入，保存照片、狀態與測試結果。
- `checkpoints/`：推論時唯讀；下載時可寫入。
- HF cache：沿用主機下載與登入資料；只有相關模式才掛載。

這些資料不包進 image，container 結束後仍留在主機。
沒有掛載出去的容器內修改會隨 `--rm` 消失。
預設輸出路徑可能重用；需要保留多次結果時，用下面的 `--output` 指定新資料夾。

### 網路、GPU、USB 為何要特別設定？

容器不會自動取得所有硬體權限，啟動腳本已依模式設定：

- `--network host`：沿用 Linux 主機網路連接手臂，不需要另開 `-p`。
- `--gpus all`：只在 `gpu-check`、`infer` 開啟 GPU。
- `--device`：`observe` 只映射指定 RealSense 的 USB／V4L 裝置，不用 `--privileged`。
- `--user`：沿用你的 UID／GID，避免輸出變成 root 所有。

詳細參數見 [Docker run 官方文件](https://docs.docker.com/reference/cli/docker/container/run/)。

### 查詢、看紀錄、進入容器

```bash
# 查看已建置的 image
docker images

# 查看正在執行的容器；加 -a 可包含已停止的容器
docker ps
docker ps -a

# 查看 Docker 使用的磁碟空間，不刪除資料
docker system df
```

以下把 `容器ID` 換成 `docker ps` 顯示的實際 ID：

```bash
# 在另一個終端機追蹤執行紀錄
docker logs -f 容器ID

# 進入正在執行的容器；exit 離開
docker exec -it 容器ID bash
```

因為使用 `--rm`，容器結束後就不能再 `logs`／`exec`；測試結果請看主機的 `policy/captures/`。
`exec` 沿用該容器權限，不會新增原本沒有掛載的 GPU／USB。

### 停止與重新執行

本頁觀察／診斷程式可在原終端機按 `Ctrl+C` 中止。
也可以在另一個終端機停止指定容器：

```bash
docker stop 容器ID
```

再次執行 `bash docker/run.sh observe` 等指令會建立新容器。
不需要 `docker start` 已被 `--rm` 刪除的容器。
**停止容器不是手臂急停，也不保證維持姿態。**
日後加入真機動作控制時，必須另行設計安全停止。

## 常用設定

### 固定設定，不用每次重打

啟動腳本現在會讀取 [`docker/runtime.env`](../docker/runtime.env)。
已設定目前手臂與相機：

```dotenv
ARM_IP=192.168.1.2
REALSENSE_SERIAL=261222076945
TROSSEN_IMAGE=trossen-pi05:local
```

新電腦可以修改這個檔案；不需要重新建置 image。
若檔案不存在，可從 [`runtime.env.example`](../docker/runtime.env.example) 複製。
格式為 `KEY=VALUE`，等號旁不加空格、值不加引號；不會執行 shell 指令。
只接受 `ARM_IP`、`REALSENSE_SERIAL`、`TROSSEN_IMAGE`、`HF_CACHE_DIR`。
終端機的環境變數優先於檔案；不要放 token 或密碼。

### 改相機／手臂

```bash
ARM_IP=192.168.1.2 REALSENSE_SERIAL=261222076945 \
  bash docker/run.sh observe
```

這只對這次執行生效。換相機時填入實際序號，不要照抄舊序號。

### 保留不同次的觀察結果

```bash
bash docker/run.sh observe --output policy/captures/session_01
```

先建立新觀察，再用它推論：

```bash
bash docker/run.sh infer-cpu \
  --image policy/captures/session_01/rgb.png \
  --task 'pick up the blue plush toy' \
  --output policy/captures/session_01_cpu
```

`--image`／`--output` 使用容器內路徑；放在 `policy/captures/` 下才會保存在主機。

### 指定 Hugging Face cache

預設沿用主機 HF cache；若原本在其他位置，先在目前 shell 設定：

```bash
export HF_CACHE_DIR=/你的路徑/huggingface
```

範例路徑請換成實際路徑。
後續 `auth`、`download`、`infer` 都會沿用它；新終端機需要重新設定。

### 只看指令，不真正執行

```bash
bash docker/run.sh --dry-run observe
```

不啟動 Docker、不連線手臂；相機未接上時會註明略過裝置映射。

<a id="migration"></a>

## 搬移到新環境

### 1. 目標電腦：優先沿用這組配置

- **系統**：Ubuntu 24.04、Intel／AMD x86_64、原生 Docker Engine。
- **GPU**：NVIDIA，主機驅動支援容器內 CUDA 12.6，另裝 Container Toolkit。
- **完整模型推論的配置建議**：24 GB 顯存、64 GB RAM；仍須實測，不是成功保證。
- **磁碟**：建議至少 100 GB 可用，容納搬移包、image、權重與下載快取。
- **硬體**：RealSense 的 USB 連接埠、可連手臂的有線網路。

這是執行完整 base 模型的保守配置方向，不是微調訓練的硬體保證。
只讀取相機／手臂，不需要大顯存 GPU。
此 image 是 `linux/amd64`，搬移工具拒絕 ARM／Mac／Windows 主機。
CUDA 驅動相容性見 [NVIDIA 官方說明](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)。

### 2. 原電腦：製作搬移包

先確認 image 已建置成功，然後執行：

```bash
cd /home/callinotch/Documents/trossen_arm
bash docker/migrate.sh export migration/trossen-pi05-20261007
```

預設包含 image 與 pi05_base 權重，約需數十 GB；複製及校驗需要時間。
輸出目錄必須不存在；重做時換一個名稱，工具不會覆寫舊包。
本次已製作 `migration/trossen-pi05-20261007/`，約 18 GB（image 匯出檔約 3.6 GB）。
只需將整個目錄搬走；image 載入後的磁碟占用會比匯出檔大。

搬移包內只有：

- `image.tar`：已建置的環境，可直接載入。
- `project/`：啟動／診斷程式、建置輸入、文件與權重。
- `image-info.txt`：原 image ID、平台與大小。
- `SHA256SUMS`：檢查檔案是否完整。

`project/` 是可執行的搬移副本，不是完整 Git repo 或整台電腦備份。
**不包含 HF token／cache、Conda、Git 歷史、舊照片或測試結果。**
若要保留舊結果，請另外複製 `policy/captures/` 到私人備份。

不帶權重的較小版本：

```bash
bash docker/migrate.sh export migration/trossen-image-only --without-checkpoint
```

這種版本到新電腦後，要重新 `download` 或自行帶入權重。
搬移工具使用官方 [docker save](https://docs.docker.com/reference/cli/docker/image/save/)／[docker load](https://docs.docker.com/reference/cli/docker/image/load/)。

### 3. 複製到新電腦、驗證

用外接 SSD 或私人檔案傳輸，複製**整個搬移包目錄**。
大型檔案不要放在單檔上限 4 GB 的 FAT32 隨身碟。
以下假設包已放在新電腦的 `~/Downloads/trossen-pi05-20261007`：

```bash
cd ~/Downloads/trossen-pi05-20261007
bash project/docker/migrate.sh verify .
```

成功標準：各檔案顯示 `OK`，程式正常結束。
校驗只偵測損壞，不驗證來源可信；只載入自己或可信任來源提供的包。

### 4. 新電腦：安裝主機工具、匯入

先完成本頁 [安裝](#安裝) 的 Docker、帳號權限與 GPU 支援。
不需要安裝 Conda、LeRobot 或主機 CUDA Toolkit，也不必重新 `build`。

```bash
cd ~/Downloads/trossen-pi05-20261007
bash project/docker/migrate.sh import . "$HOME/Documents/trossen_pi05"
cd "$HOME/Documents/trossen_pi05"
bash docker/run.sh check
bash docker/run.sh gpu-check
```

`trossen_pi05` 必須是尚不存在的新目錄，不會覆寫新電腦原本的專案。
匯入會先完整校驗，再載入 image、複製程式與權重；不會連手臂或執行模型。
若新電腦已有同名 image tag，`docker load` 會把該 tag 指向匯入版本；原 image 可能仍以 ID 保留。

### 5. 接上硬體、調整設定

使用同一支手臂與同一台 D435i，`docker/runtime.env` 的 IP／序號可沿用。
若更換硬體，先修改這個檔案。

手臂仍是 `192.168.1.2` 時，新電腦的**手臂專用有線介面**可設為：

- IPv4 手動地址 `192.168.1.1`、網路前綴 `24`（遮罩 `255.255.255.0`）。
- 直連手臂通常不填 gateway／DNS；不要因此修改其他上網介面的預設路由。
- 若 Wi-Fi／其他設備也用 `192.168.1.0/24`，先排除子網衝突，不要照抄。

先確認主機可連線，再讀取相機與手臂：

```bash
ping -c 3 192.168.1.2
bash docker/run.sh observe
```

USB 裝置編號由工具自動搜尋，不用沿用舊電腦的 `/dev/video0`。
若相機 busy，先關閉 Viewer；裝置權限仍取決於新主機設定。

### 6. 新電腦：登入、最後驗證

HF 登入資料不在包裡。若尚未登入，使用已有 PaliGemma 存取權的帳號：

```bash
bash docker/run.sh auth
```

只有沒帶權重時才補下載：

```bash
bash docker/run.sh download
```

確認 `check`、`gpu-check`、`observe` 都成功且有足夠顯存，才測 GPU 推論診斷：

```bash
bash docker/run.sh infer --task 'pick up the blue plush toy'
```

這依然不是已微調的 WidowX policy，**不會控制手臂**。
匯入成功代表環境已搬過去；真實 USB、GPU、網路與完整推論仍須在新電腦驗證。

<a id="troubleshooting"></a>

## 故障排除

### Docker daemon 無法連線

腳本訊息涵蓋「服務沒開」和「權限不足」。先看真正原因：

```bash
docker info
systemctl is-active docker
id -nG
```

- 服務是 `active`，但出現 `permission denied` → 回到 [安裝](#安裝) 步驟 2。
- 帳號已加入群組，但目前 shell 還沒有 `docker` → `newgrp docker` 或完整登出再登入。
- 服務不是 `active` → `sudo systemctl start docker`，再測 `docker info`。

不要用 `chmod 666 /var/run/docker.sock`，也不要用 `sudo bash docker/run.sh ...` 繞過問題。

### Image 尚未建置

```bash
bash docker/run.sh build
```

必須等建置成功才執行 `check`、`observe`；只安裝 Docker 不會自動產生專案 image。
若建置下載失敗，確認網路後重跑同一指令，已完成的建置層可使用快取。

### GPU 找不到

```bash
nvidia-smi
nvidia-ctk --version
bash docker/run.sh gpu-check
```

主機 `nvidia-smi` 正常、容器仍失敗 → 確認 [安裝](#安裝) 步驟 3 已完成 runtime 設定。
`check` 的 `cuda_available: false` 是正常的；以 `gpu-check` 判斷。

### CUDA out of memory（OOM）

代表顯存不足，不是 Docker 安裝失敗。
這台 8 GB GPU 已遇過此問題；改用 `infer-cpu` 只是另一個診斷途徑，不保證 RAM 足夠或速度理想。
需要另外評估低記憶體策略或更大 GPU。

### 相機 busy／找不到

關閉 Viewer 和其他串流，確認 USB 線與 `REALSENSE_SERIAL`。
容器啟動後若拔插相機，USB 裝置編號可能改變，請停止觀察後重新執行 `observe`。

### Hugging Face 401／403

確認帳號已取得 PaliGemma 存取權，再執行 `bash docker/run.sh auth`。
若用了 `HF_CACHE_DIR`，登入與推論必須指定同一個 cache。

### 手臂 CAN 通訊錯誤

先停止觀察／診斷，排除硬體通訊問題；Docker 和模型不能修復 CAN 失聯。
請看 [Trossen 官方故障排除](https://docs.trossenrobotics.com/trossen_arm/main/troubleshooting.html)。
不要在通訊異常時反覆嘗試移動或歸零。

## 版本與驗證紀錄

環境版本固定於 [requirements.lock](../docker/requirements.lock)：
Python 3.12、Trossen Arm 1.11.0、LeRobot 0.6.1、PyTorch 2.7.1＋CUDA 12.6。
Trossen 插件固定在官方 Git commit `337ed74df1ee617ddfb5987a9f7464cf3089c4a2`。

截至 2026-10-07，本次檢查確認：

- Docker 29.8.2 已安裝，服務為 `active`。
- NVIDIA Container Toolkit 1.20.1 已安裝；帳號已加入 `docker` 群組。
- 主機環境曾通過依賴、相機／手臂觀察與 policy 格式檢查。
- 已確認 image `trossen-pi05:local` 存在，平台 `linux/amd64`，約 11.7 GB。
- 容器內 `check` 與 `gpu-check` 已通過，BF16 小型運算成功。
- 搬移工具的 10 項測試已通過；包含損壞偵測、禁止覆寫、設定不執行 shell 指令。
- 真實容器 USB 與新電腦執行結果須另外驗證，不由 image 存在推定成功。
- 完整 π₀.₅ GPU 載入曾 OOM；CPU 完整推論尚未成功驗證。

Dockerfile 內含版本檢查與觀察模式單元測試；它們不代替真實硬體驗證。
