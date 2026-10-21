# WidowX 手臂與 RealSense 安裝使用

本頁整理實驗室現場說明，加上 Linux 的 RealSense 安裝。
Docker 執行方式見 [docker.md](docker.md)。

## 硬體組成

- 控制器 ×1
- 24V 變壓器 ×1
	- 不易燒壞
- 三條線，接頭有防呆
	- 電源線
	- 網路線
	- 手臂連接線
- 手臂 6 DOF＋gripper
	- 底座 1＋關節 5

## 安全規範

- **關電源前先歸原點**
	- 否則手臂會猛撞
	- 歸零：`demos/python/return_to_zero.py`
- 馬達扭力很大
	- 人容易受傷
- 操作時保持距離

## 開機與網路

1. 先開控制器電源。
2. 電腦有線網路設固定 IP。
3. 測試連線。

| 裝置 | IP |
|---|---|
| 手臂 | `192.168.1.2` |
| 電腦（例） | `192.168.1.1/24` |

- 電腦 IP 不可和手臂相同
- 只改連手臂的有線介面
	- 不填 gateway／DNS

```bash
ping -c 3 192.168.1.2
```

## 燈號

| 部位 | 燈號 | 意義 |
|---|---|---|
| 馬達 | 不亮 | 電源關，關節可自由轉動 |
| 馬達 | 綠 | 關節鎖定，不會垂下 |
| 馬達 | 藍 | 程式執行中 |
| 手臂 | 綠 | 可正常使用 |
| 手臂 | 紅 | 馬達超出範圍 |

## 程式

- 從官方 GitHub clone
	- [TrossenRobotics/trossen_arm](https://github.com/TrossenRobotics/trossen_arm)
- 範例在 `demos/python`
- 依實際末端改 `driver.configure(...)`
	- 官方範例預設 `wxai_v0_leader`
	- 本 repo 已改 `wxai_v0_follower`

`StandardEndEffector` 有三種 WXAI V0 末端，差別在 palm 質量與夾指 offset（`include/libtrossen_arm/trossen_arm_type.hpp`）：

| 末端 | palm 質量（kg） |
|---|---|
| `wxai_v0_base` | 0.5378 |
| `wxai_v0_leader` | 0.5957 |
| `wxai_v0_follower` | 0.6423 |

- 選錯會影響動力參數
	- 例如重力補償

```python
driver.configure(
    trossen_arm.Model.wxai_v0,
    trossen_arm.StandardEndEffector.wxai_v0_follower,  # 換成實際末端
    "192.168.1.2",
    False,
)
```

| 範例檔 | 用途 |
|---|---|
| `simple_move.py` | 基本動作示範 |
| `gravity_compensation.py` | 重力補償；示教、收資料 |
| `error_recovery_and_logging.py` | 除錯 |
| `return_to_zero.py` | 六關節回 0 rad |

## 資料收集

1. 先跑 `gravity_compensation.py`。
2. 握手柄下緣帶動手臂。

待決定：

- 收資料頻率多少 Hz
	- low-frequency 或 high-frequency
- 多視角相機測試
- 影像如何傳到 Linux

## 韌體更新（手臂）

- micro-USB 接電腦
	- 插控制器菱形孔
- 用官網程式更新
	- 交貨時工程師也用此法
- 步驟見 [官方韌體更新](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/firmware_upgrade.html)

## RealSense 相機

- 現有型號：D435i、D405
- 先關 RealSense Viewer
	- 才能讓程式讀相機
- D435i 接 USB 3 埠

### Linux 安裝（Ubuntu）

官方提供 Ubuntu 20／22／24／26 LTS 的預編譯套件。
來源：[librealsense Linux distribution](https://github.com/realsenseai/librealsense/blob/master/doc/distribution_linux.md)。

```bash
# 1. 加入簽章金鑰
sudo mkdir -p /etc/apt/keyrings
curl -sSf https://librealsense.realsenseai.com/Debian/librealsenseai.asc |
  gpg --dearmor | sudo tee /etc/apt/keyrings/librealsenseai.gpg >/dev/null

# 2. 加入套件來源
sudo apt-get install -y apt-transport-https
echo "deb [signed-by=/etc/apt/keyrings/librealsenseai.gpg] https://librealsense.realsenseai.com/Debian/apt-repo $(lsb_release -cs) main" |
  sudo tee /etc/apt/sources.list.d/librealsense.list
sudo apt-get update

# 3. 安裝
sudo apt-get install -y librealsense2-dkms librealsense2-utils
sudo apt-get install -y librealsense2-dev   # 可選，自己編 C++ 才需要
```

| 套件 | 內容 |
|---|---|
| `librealsense2-dkms` | 修改版 kernel module |
| `librealsense2-utils` | runtime、udev rules、`realsense-viewer` 等工具 |
| `librealsense2-dev` | 開發標頭檔（可選） |

Python 套件另外裝；Docker image 已內含 `pyrealsense2==2.56.5.9235`：

```bash
pip install pyrealsense2
```

### 驗證

重新插拔相機後：

```bash
rs-enumerate-devices       # 列出相機與序號
realsense-viewer           # 圖形介面；Depth／RGB 切 On 即可看影像
modinfo uvcvideo | grep "version:"
```

- `modinfo` 含 `realsense`
	- 代表 DKMS 模組已啟用
- DKMS 官方只列這些 kernel
	- 5.15、5.19、6.5
	- 其他 kernel 見官方手動安裝
- 本機狀態（2026-10-21）
	- kernel `7.0.0-38-generic`
	- dkms 只有 `added`，未編入
	- `uvcvideo` 為原版 `1.1.1`
	- 2026-10-07 仍成功擷取 RGB
	- 證據：`policy/captures/lerobot_verified_20261007/`
- 本機 SecureBoot 已開
	- 自編模組可能需簽章（未驗證）

### Windows

- 執行 `realsense_viewer.exe`
- Depth mode 切 On 即可用

### 相機韌體與 recovery mode

相機進入 recovery mode 時需要更新 firmware。Linux 用 `librealsense2-utils` 內附的 `rs-fw-update`：

```bash
rs-fw-update -l                       # 列出相機與韌體版本
rs-fw-update -s <序號> -f <韌體.bin>  # 更新指定相機
rs-fw-update -r -f <韌體.bin>         # 修復 recovery mode 的相機
```

- 韌體檔從 RealSense 官網下載
- 更新中不要拔線

## 配件與場地

- 相機固定架
	- CAD，3D 列印
- micro-USB 線（備用）
- C 字夾 ≥5 cm
	- 奎哥已買 2 組
- 白色圍起空間 ×1
- 固定一台 3090 電腦
	- 大家共用

## 參考文件

- [trossen_arm Python 範例](https://github.com/TrossenRobotics/trossen_arm/tree/main/demos/python)
- [Trossen 官方文件](https://docs.trossenrobotics.com/trossen_arm/main/)
- [Software setup](https://docs.trossenrobotics.com/trossen_arm/main/getting_started/software_setup.html)
- [zhl017 HackMD 安裝筆記](https://hackmd.io/@zhl017/widowx_ai)
- [Trossen AI Getting Started Guide（YouTube）](https://www.youtube.com/watch?v=XoD0Zj9VfFk)
- [librealsense Linux 安裝](https://github.com/realsenseai/librealsense/blob/master/doc/distribution_linux.md)
