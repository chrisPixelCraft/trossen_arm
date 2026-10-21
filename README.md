# WidowX＋π₀.₅

## 1. 安裝

[先裝 Docker／GPU 支援](docs/docker.md#安裝)

```bash
bash docker/run.sh build
```

## 2. 執行

相機＋手臂觀察：

```bash
bash docker/run.sh observe
```

[推論與設定](docs/docker.md)

## 文件

| 文件 | 內容 |
|---|---|
| [docs/widowx_setup.md](docs/widowx_setup.md) | 手臂接線、燈號、安全、RealSense Linux 安裝 |
| [docs/docker.md](docs/docker.md) | Docker 安裝、執行、搬移、故障排除 |
| [policy/README_LEROBOT.md](policy/README_LEROBOT.md) | 主機 Conda 流程、資料契約、記憶體實測 |
| [policy/CHECKPOINT_NOTES.md](policy/CHECKPOINT_NOTES.md) | RLinf LIBERO checkpoint 不相容原因 |
| [policy/README.md](policy/README.md) | 舊 OpenPI client 紀錄（已停用） |
