# D435i + WidowX AI Follower + OpenPI（舊紀錄）

> **已停用。** 新流程請看：
> - Docker：[docs/docker.md](../docs/docker.md)
> - 主機 Conda：[README_LEROBOT.md](README_LEROBOT.md)
>
> 本頁保留先前獨立 OpenPI client 的準備紀錄。
> 文中的 `policy/client-venv` 已移至 `/tmp/trossen-unused-environments.GuTHCh/`。

## 當時完成的內容

- 獨立客戶端環境
- 相機與關節狀態預覽
- OpenPI WebSocket 推論介面
- 不下達移動或夾爪指令
	- 連接／清理仍管理控制器
	- 先停止其他手臂程式

所有指令從 `/home/callinotch/Documents/trossen_arm` 執行。

## 相機與手臂

先關 RealSense Viewer，避免佔用相機。

```bash
# 列出相機（不啟動串流）
policy/client-venv/bin/python policy/camera_policy_client.py --list-cameras --headless

# 只預覽相機
policy/client-venv/bin/python policy/camera_policy_client.py --camera-only

# 預覽相機＋讀 Follower 狀態；Q 或 Ctrl+C 結束
policy/client-venv/bin/python policy/camera_policy_client.py

# 無視窗，跑 60 幀並存最後一筆
policy/client-venv/bin/python policy/camera_policy_client.py \
  --headless --frames 60 --snapshot policy/captures/check
```

| 預設 | 值 |
|---|---|
| 手臂 | `wxai_v0` / `wxai_v0_follower` / `192.168.1.2` |
| 相機 | D435i，序號 `261222076945` |
| 彩色影像 | 640 × 480、RGB、30 FPS |

- 快照存 `rgb.png`、`state.json`
- 只是觀察快照
	- 沒有示範動作
	- 不能直接訓練

## Policy 輸入／輸出

| 欄位 | 格式 |
|---|---|
| `state` | float32 `[7]`，joint 0–5（rad）＋夾爪位置（m） |
| `images.cam_high` | uint8 RGB `[3, 480, 640]`，CHW |
| `prompt` | 任務文字，需符合訓練設定 |
| 回應 `actions` | 有限數值 `[action_horizon, 7]`，只印出、永不執行 |

這是本客戶端的單臂介面，不是所有 OpenPI checkpoint 的通用格式。Server 必須依 checkpoint 訓練設定轉換以下項目：

- 影像縮放、相機名稱
- 狀態／動作正規化
- 關節順序、夾爪單位
- absolute／delta 動作

限制：

- 7 維檢查只看形狀
	- 不證明權重相容
- 不可直接套 DROID
- 不可直接套雙臂 ALOHA
	- 也不可補零假裝雙臂

匹配的 π₀.₅ server 啟動後：

```bash
policy/client-venv/bin/python policy/camera_policy_client.py \
  --server 127.0.0.1 --port 8000 --task "pick up the block"
```

- 任務文字只是示例
- 約每秒最多推論一次
	- 用於整合診斷
	- 不是即時控制迴圈

## OpenPI 與模型環境

- 原始碼在 `policy/openpi/`
	- 官方 main 淺層 clone
- `client-venv` 只裝 `openpi-client`
	- 不是完整推論環境
- 完整 OpenPI 需 Python ≥ 3.11
	- 3.10 的 venv 不能跑模型
	- server 依官方 README 另建
- RTX 4060 Laptop 8 GB
	- 低於官方 >8 GB 需求
	- 需實測記憶體與延遲
- 當時狀態
	- 未下載權重
	- 未啟動 server
	- 未執行預測動作
- RLinf LIBERO checkpoint 不相容
	- 見 [CHECKPOINT_NOTES.md](CHECKPOINT_NOTES.md)

重建客戶端環境：

```bash
python -m venv policy/client-venv
policy/client-venv/bin/python -m pip install \
  -r policy/requirements-client.txt ./policy/openpi/packages/openpi-client
```

## 來源

- [OpenPI](https://github.com/Physical-Intelligence/openpi)
- [OpenPI remote inference](https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md)
- [Trossen OpenPI 教學](../docs/tutorials/openpi.rst)
