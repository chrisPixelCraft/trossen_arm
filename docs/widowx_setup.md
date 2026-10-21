# WidowX 手臂與 RealSense 安裝使用

實驗室現場說明＋Linux RealSense 安裝。Docker 執行方式見 [docker.md](docker.md)。

## 安全規範

- **關電源前先歸原點**，否則手臂會猛撞（歸零：`demos/python/return_to_zero.py`）
- 馬達扭力很大，人容易受傷；操作時保持距離

## 硬體與接線

| 元件 | 說明 |
|---|---|
| 控制器 ×1 | 搭配 24V 變壓器（不易燒壞） |
| 三條線 | 電源線、網路線、手臂連接線；接頭有防呆 |
| 手臂 | 6 DOF＋gripper（底座 1＋關節 5） |

## 開機與網路

1. 先開控制器電源
2. 電腦**連手臂的有線介面**設固定 IP `192.168.1.1/24`（不可和手臂的 `192.168.1.2` 相同；不填 gateway／DNS）
3. 測試連線：`ping -c 3 192.168.1.2`

## 燈號

| 部位 | 燈號 | 意義 |
|---|---|---|
| 馬達 | 不亮 | 電源關，關節可自由轉動 |
| 馬達 | 綠 | 關節鎖定，不會垂下 |
| 馬達 | 藍 | 程式執行中 |
| 手臂 | 綠 | 可正常使用 |
| 手臂 | 紅 | 馬達超出範圍 |

## 程式

範例在 `demos/python`（來自 [官方 GitHub](https://github.com/TrossenRobotics/trossen_arm)）。
`driver.configure(...)` 的末端要符合實體：官方範例預設 `wxai_v0_leader`，本 repo 已改成 `wxai_v0_follower`。

```python
driver.configure(
    trossen_arm.Model.wxai_v0,
    trossen_arm.StandardEndEffector.wxai_v0_follower,  # 換成實際末端
    "192.168.1.2",
    False,
)
```

三種末端的差別在 palm 質量與夾指 offset；選錯會讓動力參數（例如重力補償）不準。
來源：`include/libtrossen_arm/trossen_arm_type.hpp`。

| 末端 | palm 質量（kg） |
|---|---|
| `wxai_v0_base` | 0.5378 |
| `wxai_v0_leader` | 0.5957 |
| `wxai_v0_follower` | 0.6423 |

| 範例檔 | 用途 |
|---|---|
| `simple_move.py` | 基本動作示範 |
| `gravity_compensation.py` | 重力補償；示教、收資料 |
| `error_recovery_and_logging.py` | 除錯 |
| `return_to_zero.py` | 六關節回 0 rad |

## 資料收集

先跑 `gravity_compensation.py`，再握手柄下緣帶動手臂。

**待決定：**

- 收資料頻率（low- 或 high-frequency）
- 多視角相機測試
- 影像如何傳到 Linux

## 手臂韌體更新

micro-USB 一端接電腦、一端插控制器菱形孔，用官網程式更新（交貨時工程師也用此法）。
步驟見 [官方韌體更新](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/firmware_upgrade.html)。

## RealSense 相機

現有型號 D435i、D405。D435i 接 USB 3 埠；程式讀相機前先關 RealSense Viewer。

### Linux 安裝（Ubuntu）

官方提供 Ubuntu 20／22／24／26 LTS 預編譯套件（[來源](https://github.com/realsenseai/librealsense/blob/master/doc/distribution_linux.md)）。

```bash
# 1. 簽章金鑰
sudo mkdir -p /etc/apt/keyrings
curl -sSf https://librealsense.realsenseai.com/Debian/librealsenseai.asc |
  gpg --dearmor | sudo tee /etc/apt/keyrings/librealsenseai.gpg >/dev/null

# 2. 套件來源
sudo apt-get install -y apt-transport-https
echo "deb [signed-by=/etc/apt/keyrings/librealsenseai.gpg] https://librealsense.realsenseai.com/Debian/apt-repo $(lsb_release -cs) main" |
  sudo tee /etc/apt/sources.list.d/librealsense.list
sudo apt-get update

# 3. 安裝
sudo apt-get install -y librealsense2-dkms librealsense2-utils
sudo apt-get install -y librealsense2-dev   # 可選，自己編 C++ 才需要

# 4. Python（Docker image 已內含 pyrealsense2==2.56.5.9235）
pip install pyrealsense2
```

| 套件 | 內容 |
|---|---|
| `librealsense2-dkms` | 修改版 kernel module |
| `librealsense2-utils` | runtime、udev rules、`realsense-viewer` 等工具 |
| `librealsense2-dev` | 開發標頭檔 |

### 驗證

重新插拔相機後：

```bash
rs-enumerate-devices                 # 列出相機與序號
realsense-viewer                     # Depth／RGB 切 On 看影像
modinfo uvcvideo | grep "version:"   # 含 realsense → DKMS 模組已啟用
```

DKMS 官方只支援 kernel 5.15、5.19、6.5；其他 kernel 見官方手動安裝。

**本機狀態（2026-10-21）：**

| 項目 | 狀態 |
|---|---|
| Kernel | `7.0.0-38-generic`（不在支援清單） |
| DKMS | 只有 `added`，未編入 kernel |
| `uvcvideo` | 原版 `1.1.1` |
| RGB 擷取 | 2026-10-07 仍成功（`policy/captures/lerobot_verified_20261007/`） |
| SecureBoot | 已開；自編模組可能需簽章（未驗證） |

### Windows

執行 `realsense_viewer.exe`，Depth mode 切 On 即可用。

### 相機韌體與 recovery mode

相機進入 recovery mode 時要更新 firmware。韌體檔從 RealSense 官網下載，更新中不要拔線。

```bash
rs-fw-update -l                       # 列出相機與韌體版本
rs-fw-update -s <序號> -f <韌體.bin>  # 更新指定相機
rs-fw-update -r -f <韌體.bin>         # 修復 recovery mode 的相機
```

## 配件與場地

| 項目 | 說明 |
|---|---|
| 相機固定架 | CAD，3D 列印 |
| micro-USB 線 | 備用 |
| C 字夾 ≥5 cm | 奎哥已買 2 組 |
| 場地 | 白色圍起空間 ×1 |
| 電腦 | 固定一台 3090，大家共用 |

## 參考文件

- Trossen：[官方文件](https://docs.trossenrobotics.com/trossen_arm/main/)、[Software setup](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/software_setup.html)、[Python 範例](https://github.com/TrossenRobotics/trossen_arm/tree/main/demos/python)
- 教學：[zhl017 HackMD](https://hackmd.io/@zhl017/widowx_ai)、[Getting Started 影片](https://www.youtube.com/watch?v=XoD0Zj9VfFk)
- RealSense：[librealsense Linux 安裝](https://github.com/realsenseai/librealsense/blob/master/doc/distribution_linux.md)
