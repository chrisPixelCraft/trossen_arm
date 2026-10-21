# OpenPI client（舊紀錄，已停用）

> 新流程：Docker 看 [docs/docker.md](../docs/docker.md)；主機 Conda 看 [README_LEROBOT.md](README_LEROBOT.md)。
> 下方的 `policy/client-venv` 已移到 `/tmp/trossen-unused-environments.GuTHCh/`，指令需先重建環境才能用。

當時做了：獨立客戶端環境、D435i＋Follower 狀態預覽、OpenPI WebSocket 推論介面。
程式不下移動或夾爪指令，但連接／清理仍會管理控制器，執行前先停止其他手臂程式。
所有指令從 `/home/callinotch/Documents/trossen_arm` 執行。

## 相機與手臂

先關 RealSense Viewer。

```bash
PY=policy/client-venv/bin/python
$PY policy/camera_policy_client.py --list-cameras --headless   # 列出相機，不串流
$PY policy/camera_policy_client.py --camera-only               # 只預覽相機
$PY policy/camera_policy_client.py                             # 相機＋Follower 狀態；Q／Ctrl+C 結束
$PY policy/camera_policy_client.py \
  --headless --frames 60 --snapshot policy/captures/check      # 存 rgb.png、state.json
```

| 預設 | 值 |
|---|---|
| 手臂 | `wxai_v0` / `wxai_v0_follower` / `192.168.1.2` |
| 相機 | D435i，序號 `261222076945` |
| 彩色影像 | 640 × 480、RGB、30 FPS |

快照只是觀察資料，沒有示範動作，不能直接訓練。

## Policy 輸入／輸出

| 欄位 | 格式 |
|---|---|
| `state` | float32 `[7]`：joint 0–5（rad）＋夾爪位置（m） |
| `images.cam_high` | uint8 RGB `[3, 480, 640]`，CHW |
| `prompt` | 任務文字，需符合訓練設定 |
| 回應 `actions` | 有限數值 `[action_horizon, 7]`；只印出，永不執行 |

這是本客戶端的單臂介面，不是 OpenPI 通用格式。Server 必須依 checkpoint 訓練設定處理：影像縮放、相機名稱、狀態／動作正規化、關節順序、夾爪單位、absolute／delta。

- 7 維檢查只看形狀，不證明權重相容
- 不可直接套 DROID 或雙臂 ALOHA，也不可補零假裝第二支手臂

```bash
$PY policy/camera_policy_client.py \
  --server 127.0.0.1 --port 8000 --task "pick up the block"
```

任務文字只是示例。推論約每秒最多一次，只用於整合診斷，不是即時控制迴圈。

## 環境

- `policy/openpi/`：官方 main 的淺層 clone
- `client-venv`（Python 3.10）只裝 `openpi-client`；完整 OpenPI 需 Python ≥ 3.11，server 要依官方 README 另建
- RTX 4060 Laptop 8 GB 低於官方 >8 GB 需求，需實測記憶體與延遲
- 當時未下載權重、未啟動 server、未執行任何預測動作
- RLinf LIBERO checkpoint 不相容，見 [CHECKPOINT_NOTES.md](CHECKPOINT_NOTES.md)

```bash
python -m venv policy/client-venv
policy/client-venv/bin/python -m pip install \
  -r policy/requirements-client.txt ./policy/openpi/packages/openpi-client
```

來源：[OpenPI](https://github.com/Physical-Intelligence/openpi)、[remote inference](https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md)、[Trossen OpenPI 教學](../docs/tutorials/openpi.rst)
