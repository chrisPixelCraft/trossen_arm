# RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT

檢查日期：2026-10-07。

## 結論

- 不能直接用在 WidowX
	- 為 LIBERO 模擬訓練
	- 未做實體部署驗證
- 不相容目前相機客戶端
	- 輸入介面不同
- 沒有零樣本部署證據

## 介面差異

| 項目 | 目前實體設定 | RLinf LIBERO |
|---|---|---|
| 相機 | 一台 D435i 固定全景 | 全景＋腕部 |
| 狀態 | 6 關節角＋夾爪位置，7 維 | 末端 xyz＋angle-axis＋兩夾指，8 維 |
| 動作 | SDK 關節角等命令 | 模擬環境定義，delta actions |
| 輸入欄位 | `state`<br>`images.cam_high`<br>`prompt` | `observation/state`<br>`observation/image`<br>`observation/wrist_image`<br>`prompt` |

**證據：**

- LIBERO 狀態的組成
	- 程式 `_extract_image_and_state`
	- `robot0_eef_pos`
	- `quat2axisangle(robot0_eef_quat)`
	- `robot0_gripper_qpos`
- RLinf 資料轉換說明
	- 原始動作已是 delta
- 輸出雖然也是 7 維
	- 不等於 6 關節＋夾爪
	- 改欄位名、補零都無效

## 檔案與載入

| 檔案 | 大小 | 推論需要？ |
|---|---|---|
| `model.safetensors` | 7,473,091,464 bytes | 是 |
| `optimizer.pt` | 13,473,854,709 bytes | 否 |
| `physical-intelligence/libero/norm_stats.json` | 小 | 是 |

- 布局與 upstream OpenPI 不同
	- 需依 RLinf 方式載入
	- 不能只填進 `serve_policy`
- 檔案大小 ≠ 推論顯存
	- 另需中間張量
	- 另需 KV cache
- 只查過 metadata 與 `norm_stats`
	- 沒下載權重

## 下一步

- 現在可做
	- 測相機與關節擷取
- 測這個 checkpoint
	- 在 LIBERO 流程跑
	- 不連接硬體
	- 確認格式與顯存
- 做實體桌面操作
	- 定義相容控制介面
	- 對齊相機與末端座標
	- 定義夾爪映射
	- 用實體示範驗證／微調

## 來源

- [模型頁面](https://huggingface.co/RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT)
- [模型檔案清單](https://huggingface.co/RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT/tree/main)
- [RLinf LIBERO 環境](https://github.com/RLinf/RLinf/blob/main/rlinf/envs/sim/libero/libero_env.py)
- [RLinf LIBERO Policy](https://github.com/RLinf/RLinf/blob/main/rlinf/models/embodiment/openpi/policies/libero_policy.py)
- [RLinf LIBERO 資料轉換](https://github.com/RLinf/RLinf/blob/main/rlinf/models/embodiment/openpi/dataconfig/libero_dataconfig.py)
