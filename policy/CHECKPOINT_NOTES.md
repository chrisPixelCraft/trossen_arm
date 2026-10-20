# RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT

檢查日期：2026-10-07。

這組權重用於 LIBERO 模擬環境，尚未完成 WidowX AI Follower 的部署驗證。
目前相機客戶端不能直接使用這組權重的預設 LIBERO 輸入介面。

## 已確認的差異

| 項目 | 目前實體設定 | RLinf LIBERO 介面 |
| --- | --- | --- |
| 相機 | 一台 D435i 固定全景相機 | 全景 + 腕部影像 |
| 狀態 | 6 個關節角度 + 1 個夾爪位置，7 維 | 末端 xyz + angle-axis 旋轉 + 兩個夾指位置，8 維 |
| 動作 | SDK 可接受關節角度等命令 | 模擬環境的動作定義；不能把 7 維輸出直接當成 6 個關節目標 + 夾爪位置 |
| 輸入欄位 | `state`, `images.cam_high`, `prompt` | `observation/state`, `observation/image`, `observation/wrist_image`, `prompt` |

LIBERO 的環境程式在 `_extract_image_and_state` 使用
`robot0_eef_pos`、`quat2axisangle(robot0_eef_quat)`、`robot0_gripper_qpos`
組成狀態。RLinf 的資料轉換程式說明原始 LIBERO 動作已是 delta actions。
不能僅修改欄位名稱、補零或看到輸出也是 7 維就假設相容。

Hugging Face 檔案清單列出：

- `model.safetensors`：7,473,091,464 bytes。
- `optimizer.pt`：13,473,854,709 bytes，推論不需要此訓練 optimizer 檔。
- 正規化資料：`physical-intelligence/libero/norm_stats.json`。

這個資料布局與 upstream OpenPI 預設 checkpoint assets 布局也不同；
需要依 RLinf 的載入／轉換方式檢查，不能只把模型 ID 填進 upstream serve_policy。
模型檔大小不等於推論顯存，還需計入中間張量、KV cache 等記憶體。
目前只查詢 metadata 與小型 norm_stats 檔，沒有下載權重。

## 下一步

目前可先測固定相機與實體關節狀態擷取。
若要測這個 checkpoint，先在與它匹配的 LIBERO 流程中做不連接硬體的推論，
確認模型格式及本機顯存是否可用。
若目標是實體 WidowX 桌面操作，需要定義相容的控制介面、相機與末端座標、
夾爪映射，並以實體示範資料驗證／微調；目前沒有證據支持直接零樣本部署。

來源：

- [模型頁面](https://huggingface.co/RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT)
- [模型檔案清單](https://huggingface.co/RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT/tree/main)
- [RLinf LIBERO 環境](https://github.com/RLinf/RLinf/blob/main/rlinf/envs/sim/libero/libero_env.py)
- [RLinf LIBERO Policy](https://github.com/RLinf/RLinf/blob/main/rlinf/models/embodiment/openpi/policies/libero_policy.py)
- [RLinf LIBERO 資料轉換](https://github.com/RLinf/RLinf/blob/main/rlinf/models/embodiment/openpi/dataconfig/libero_dataconfig.py)
