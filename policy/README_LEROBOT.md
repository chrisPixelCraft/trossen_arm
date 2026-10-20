# LeRobot + WidowX Follower + π₀.₅

全部使用既有 Conda 環境 `trossen_ai_env`，不使用新的 venv。
此環境原為 Python 3.10，為符合 Trossen 官方 LeRobot 插件已就地升級到 Python 3.12。
升級前的版本記錄在 `trossen_env_before_lerobot.txt`。
之前的 `client-venv` 與 `lerobot_workspace/.venv` 已移至
`/tmp/trossen-unused-environments.GuTHCh/` 保留，以下流程不使用它們。
`README.md` 的舊 OpenPI client 指令不是本流程入口。

## 啟用環境

```bash
source /home/callinotch/miniconda3/etc/profile.d/conda.sh
conda activate trossen_ai_env
cd /home/callinotch/Documents/trossen_arm
```

## 相機與手臂觀察

關閉 RealSense Viewer，並停止其他連接手臂的程式。

```bash
python policy/lerobot_observe.py
```

預設讀取 D435i（序號 `261222076945`）與 Follower（`192.168.1.2`），
採用官方 LeRobot 插件的 feature 名稱與觀察介面。
程式不下達移動指令，也不會執行官方插件原本在 connect/disconnect 時的 staged moves。
驅動清理連線仍會處理 idle；請勿同時執行其他手臂控制程式。
預設讀取 60 幀，最後儲存 `policy/captures/lerobot_check/rgb.png`
與 `observation.json`。

這是觀察快照，不是示範資料。模型訓練需要同時含 observation、expert action、
時間及任務文字的 LeRobot dataset。

## 單臂資料契約

| 欄位 | 定義 |
| --- | --- |
| `observation.state` | `[joint_0 … joint_5, left_carriage_joint]`，7 維 |
| 關節單位 | 前六項 rad，夾爪 m |
| `observation.images.image` | D435i RGB，640 × 480 × 3 |
| `action` | 相同順序的七個 absolute 目標位置；需用此定義的示範微調 |

π₀.₅ 內部可以補到 32 維；外部資料保持 7 維。
這不是把 LIBERO 權重的輸出改成 7 就能直接使用。
你提供的 RLinf LIBERO checkpoint 相容性差異見 `CHECKPOINT_NOTES.md`。

## π₀.₅ 設定與 GPU 檢查

```bash
python policy/pi05_preflight.py
```

此指令建立 7 維的 policy 設定，測試小型 BF16 GPU 運算，並用 meta tensors
計算完整 π₀.₅ 架構的參數記憶體；不下載權重、不進行模型推論、不連接手臂。
輸出在 `policy/captures/pi05_preflight/`。`config.json` 是待訓練設定，
不是已訓練的 checkpoint。
記憶體估計尚未包含 activations、KV cache、gradients、optimizer，
所以不能把參數能放進 GPU 視為訓練或推論已成功。

本機已測得 LeRobot 0.6.1 的 BF16／混合精度模型參數約 8.71 GiB，
GPU 總計約 7.62 GiB、當時可用約 7.51 GiB；標準整個模型放上 GPU 不可行。
這是 meta 架構估計，並非實際 GPU 推論的峰值測量。

## 官方 checkpoint 與 CPU 推論診斷

已下載 `lerobot/pi05_base` 到 `checkpoints/pi05_base`。
`model.safetensors` 為 14,467,165,872 bytes，並通過 813 個 state tensor 的名稱／尺寸檢查。
使用它作為七維 WidowX dataset 的微調起點時，應使用
`--policy.type=pi05 --policy.pretrained_path=checkpoints/pi05_base`，
讓 feature 名稱與七維定義來自你的資料；不是直接繼承 base 的三相機／32 維設定。
原始 checkpoint 檔不修改。

取得 Google PaliGemma 的 tokenizer 存取權並登入：

```bash
hf auth login
```

先做不載入完整模型的權重檢查：

```bash
python policy/pi05_infer_cpu.py --check-weights-only
```

以相機快照與測試指令執行 CPU 推論：

```bash
python policy/pi05_infer_cpu.py \
  --image policy/captures/lerobot_verified_20261007/rgb.png \
  --task "pick up the blue plush toy"
```

此測試使用人工的 normalized 零狀態，並保留 base 原生 32 維輸出。
結果儲存於 `policy/captures/pi05_cpu_inference/`。
不包含真實 WidowX 狀態／動作正規化，不是可直接操作 WidowX 的 policy。
程式沒有手臂連線或動作指令，只用來驗證權重、影像／文字管線與數值運算。
真正的七維動作推論需要相應示範資料、正規化資料與微調 checkpoint。

## 安裝重現

官方插件原始碼在 `policy/lerobot_trossen`，本機 editable 安裝。
使用 `uv pip` 指定現有環境，而不是 `uv sync`（後者可能建立新 venv）：

```bash
uv pip install --python "$CONDA_PREFIX/bin/python" --torch-backend cu126 \
  --index https://pypi.nvidia.com \
  -r policy/requirements-lerobot.txt
```

`requirements-lerobot.txt` 固定 LeRobot 0.6.1、Trossen Arm 1.11.0、
PyTorch 2.7.1、TorchVision 0.22.1、TorchCodec 0.3.0。

## 尚需完成

- 確定任務與示範操作方式（目前只有 Follower，没有 Leader）。
- 錄製可訓練的單臂示範資料。
- 實測 π₀.₅ 模型記憶體與推論，再決定本機可行的微調／部署方式。
- 使用相容權重與處理器，驗證動作單位與範圍後才執行實體動作。

來源：

- [LeRobot π₀.₅](https://huggingface.co/docs/lerobot/en/pi05)
- [Trossen LeRobot 插件](https://github.com/TrossenRobotics/lerobot_trossen)
