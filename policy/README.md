# D435i + WidowX AI Follower + OpenPI

> 目前改用既有 `trossen_ai_env` 的 LeRobot 流程，請從
> [README_LEROBOT.md](README_LEROBOT.md) 開始。
> 以下為先前的獨立 OpenPI client 準備記錄，不再作為操作入口。

目前已建立獨立的客戶端環境、相機與關節狀態預覽，以及 OpenPI
WebSocket 推論介面。程式不下達移動或夾爪施力指令。
連接／清理驅動會管理控制器連線，請先停止其他手臂程式。

所有指令從 `/home/callinotch/Documents/trossen_arm` 執行。

## 相機與手臂

先關閉 RealSense Viewer，避免佔用相機。

列出相機（不啟動影像串流）：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py --list-cameras --headless
```

僅預覽相機：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py --camera-only
```

預覽相機並讀取 Follower 狀態：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py
```

按 Q 或 Ctrl+C 結束。預設設定：

- 手臂：`wxai_v0` / `wxai_v0_follower` / `192.168.1.2`
- 相機：D435i，序號 `261222076945`
- 彩色影像：640 × 480、RGB、30 FPS

不用開視窗，測試 60 幀並儲存最後一筆觀察資料：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py \
  --headless --frames 60 --snapshot policy/captures/check
```

會儲存 `rgb.png` 和 `state.json`。這是觀察快照，沒有示範動作，
不是可直接用於訓練的資料集。

## Policy 輸入／輸出

本客戶端的單臂介面如下。Server 必須依模型的訓練設定做對應轉換；
以下欄位不是所有 OpenPI checkpoint 都支援的通用格式。

| 欄位 | 格式 |
| --- | --- |
| `state` | float32 `[7]`，joint 0–5（rad），最後為夾爪位置（m） |
| `images.cam_high` | uint8 RGB `[3, 480, 640]`，CHW |
| `prompt` | 任務文字，需與模型訓練設定相符 |
| 回應 `actions` | 有限數值 `[action_horizon, 7]`；只印出，永不執行 |

Server 的影像縮放、相機名稱、狀態／動作正規化、關節順序、夾爪單位、
absolute / delta 動作必須與 checkpoint 的訓練設定相同。
7 維檢查只檢查資料形狀，不能證明權重與硬體相容。
不要直接套用 DROID 或雙臂 ALOHA checkpoint，也不要補零假裝另一支手臂存在。

當匹配的 π₀.₅ server 已啟動時，客戶端可執行：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py \
  --server 127.0.0.1 --port 8000 --task "pick up the block"
```

任務文字只是示例，請換成 checkpoint 支援的任務。
推論最多約每秒一次，用於整合診斷，不是即時動作控制迴圈。

## OpenPI 與模型環境

官方原始碼位於 `policy/openpi/`，由官方 main branch 的淺層 clone 取得。
`openpi-client` 已裝在 `policy/client-venv`，不代表完整模型推論環境已安裝。
完整 OpenPI 需要 Python ≥ 3.11，因此 Python 3.10 的 client-venv 不能用來跑模型。
Server 應另外依官方 README 建立環境。

本機 RTX 4060 Laptop 有 8 GB 顯存，低於官方標準推論需求（>8 GB）。
取得權重路徑與訓練設定後，先測模型載入與不控制硬體的推論，實測記憶體與延遲。
目前未下載模型權重，未啟動模型 server，也未執行模型預測的動作。

你提供的 `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT` 尚不相容於本客戶端的
單臂關節介面，具體差異見 [CHECKPOINT_NOTES.md](CHECKPOINT_NOTES.md)。

重建客戶端環境：

```bash
python -m venv policy/client-venv
policy/client-venv/bin/python -m pip install \
  -r policy/requirements-client.txt ./policy/openpi/packages/openpi-client
```

來源：

- [OpenPI](https://github.com/Physical-Intelligence/openpi)
- [OpenPI remote inference](https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md)
- [Trossen OpenPI 教學](../docs/tutorials/openpi.rst)
