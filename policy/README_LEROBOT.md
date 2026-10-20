# LeRobot + WidowX Follower + π₀.₅

主機 Conda 流程。Docker 流程見 [docs/docker.md](../docs/docker.md)。

## 現況

| 項目 | 狀態 |
|---|---|
| 相機＋手臂觀察 | 可用，不移動手臂 |
| π₀.₅ 設定／GPU 檢查 | 可用，不載入權重 |
| `pi05_base` 權重 | 已下載、通過名稱／尺寸檢查 |
| 完整 GPU 推論 | 8 GB 顯存不足 |
| WidowX 7 維 policy | 尚無，需示範資料＋微調 |

## 環境

- 只用 Conda `trossen_ai_env`
	- 不建新 venv
- 已升到 Python 3.12
	- 原為 3.10
	- 為了 Trossen LeRobot 插件
	- 舊版記錄在 `trossen_env_before_lerobot.txt`
- 舊環境已停用
	- `client-venv`、`lerobot_workspace/.venv`
	- 移至 `/tmp/trossen-unused-environments.GuTHCh/`
- [README.md](README.md) 是舊 OpenPI 紀錄
	- 不是本流程入口

```bash
source /home/callinotch/miniconda3/etc/profile.d/conda.sh
conda activate trossen_ai_env
cd /home/callinotch/Documents/trossen_arm
```

## 相機與手臂觀察

先關 RealSense Viewer，並停止其他手臂程式。

```bash
python policy/lerobot_observe.py
```

- 預設裝置
	- D435i 序號 `261222076945`
	- Follower `192.168.1.2`
- 使用官方插件的 feature 名稱
- 不下達移動指令
	- 跳過插件的 staged moves
	- 清理連線仍會 idle
- 讀 60 幀後儲存
	- `policy/captures/lerobot_check/rgb.png`
	- `policy/captures/lerobot_check/observation.json`

這只是觀察快照，不是示範資料。訓練需要同時包含 observation、expert action、時間與任務文字的 LeRobot dataset。

## 單臂資料契約

| 欄位 | 定義 |
|---|---|
| `observation.state` | `[joint_0 … joint_5, left_carriage_joint]`，7 維 |
| 單位 | 前六項 rad，夾爪 m |
| `observation.images.image` | D435i RGB，640 × 480 × 3 |
| `action` | 同順序的 7 個 absolute 目標位置 |

- π₀.₅ 內部補到 32 維
	- 外部資料保持 7 維
- `action` 需用此定義微調
- LIBERO 權重不能直接用
	- 改輸出維度無效
	- 見 [CHECKPOINT_NOTES.md](CHECKPOINT_NOTES.md)

## π₀.₅ 設定與 GPU 檢查

```bash
python policy/pi05_preflight.py
```

- 會做的事
	- 建立 7 維 policy 設定
	- 測小型 BF16 GPU 運算
	- 用 meta tensors 估參數記憶體
- 不做的事
	- 不下載權重、不推論
	- 不連接手臂
- 輸出 `policy/captures/pi05_preflight/`
	- `config.json` 是待訓練設定
	- 不是已訓練 checkpoint

**實測結果（LeRobot 0.6.1）：**

| 項目 | 數值 |
|---|---|
| BF16／混合精度參數 | 約 8.71 GiB |
| GPU 總量 | 約 7.62 GiB |
| 當時可用 | 約 7.51 GiB |

- 整個模型放上 GPU 不可行
- 這是 meta 架構估計
	- 不是推論峰值實測
	- 未含 activations、KV cache
	- 未含 gradients、optimizer

## 官方 checkpoint 與 CPU 推論診斷

- 已下載 `lerobot/pi05_base`
	- 位置 `checkpoints/pi05_base`
	- `model.safetensors` 14,467,165,872 bytes
	- 813 個 tensor 名稱／尺寸通過
- 原始 checkpoint 不修改
- 作為微調起點時用：
	- `--policy.type=pi05`
	- `--policy.pretrained_path=checkpoints/pi05_base`
	- feature 定義來自你的資料
	- 不繼承 base 的三相機／32 維

取得 [Google PaliGemma](https://huggingface.co/google/paligemma-3b-pt-224) tokenizer 存取權後登入：

```bash
hf auth login
```

先做不載入完整模型的權重檢查，再跑 CPU 推論：

```bash
python policy/pi05_infer_cpu.py --check-weights-only

python policy/pi05_infer_cpu.py \
  --image policy/captures/lerobot_verified_20261007/rgb.png \
  --task "pick up the blue plush toy"
```

- 輸出 `policy/captures/pi05_cpu_inference/`
- 輸入是人工零狀態
	- 已 normalized
	- 保留 base 原生 32 維輸出
- 沒有 WidowX 正規化
	- **不能操作 WidowX**
- 沒有手臂連線或動作指令
- 只驗證三件事
	- 權重
	- 影像／文字管線
	- 數值運算

真正的 7 維動作推論需要對應的示範資料、正規化資料與微調 checkpoint。

## 安裝重現

- 插件在 `policy/lerobot_trossen`
	- editable 安裝
- 用 `uv pip` 指定現有環境
	- 不用 `uv sync`
	- 後者可能建新 venv

```bash
uv pip install --python "$CONDA_PREFIX/bin/python" --torch-backend cu126 \
  --index https://pypi.nvidia.com \
  -r policy/requirements-lerobot.txt
```

`requirements-lerobot.txt` 固定版本：

| 套件 | 版本 |
|---|---|
| LeRobot | 0.6.1 |
| Trossen Arm | 1.11.0 |
| PyTorch | 2.7.1 |
| TorchVision | 0.22.1 |
| TorchCodec | 0.3.0 |

## 尚需完成

- 確定任務與示範方式
	- 目前只有 Follower
	- 沒有 Leader
- 錄製單臂示範資料
- 實測 π₀.₅ 記憶體與推論
	- 再決定微調／部署方式
- 用相容權重與處理器
	- 驗證動作單位與範圍
	- 之後才執行實體動作

來源：

- [LeRobot π₀.₅](https://huggingface.co/docs/lerobot/en/pi05)
- [Trossen LeRobot 插件](https://github.com/TrossenRobotics/lerobot_trossen)
