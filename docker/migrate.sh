#!/usr/bin/env bash
# Portable, allowlisted migration bundle. Never export HF login/cache or captures.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$project_root/docker/read_config.sh"
load_runtime_config "$project_root/docker/runtime.env"
image_name="${TROSSEN_IMAGE:-trossen-pi05:local}"

die() { printf '%s\n' "$*" >&2; exit 1; }
usage() {
    printf '%s\n' \
        'bash docker/migrate.sh export BUNDLE_DIR [--without-checkpoint]' \
        'bash docker/migrate.sh verify BUNDLE_DIR' \
        'bash docker/migrate.sh import BUNDLE_DIR NEW_PROJECT_DIR'
}
require_host() {
    [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || die '目前只支援 Linux x86_64 主機。'
    command -v docker >/dev/null || die '請先安裝 Docker。'
    docker info >/dev/null 2>&1 || die 'Docker 無法連線；請檢查服務與帳號權限。'
}
verify_bundle() {
    local bundle_path="$1"
    [[ -f "$bundle_path/SHA256SUMS" && -f "$bundle_path/image.tar" &&
       -f "$bundle_path/project/docker/run.sh" && -f "$bundle_path/image-info.txt" ]] || die '搬移包不完整。'
    # Accept only our own fixed image files and relative project file paths.
    # Checksums detect corruption, not malicious/tampered bundles; use trusted sources only.
    while IFS= read -r checksum_line; do
        [[ "$checksum_line" =~ ^[a-f0-9]{64}\ \ (image\.tar|image-info\.txt|project/[A-Za-z0-9_./-]+)$ ]] || die 'SHA256SUMS 格式不正確。'
        local checksum_path="${checksum_line:66}"
        [[ "/$checksum_path/" != *'/../'* && "/$checksum_path/" != *'/./'* ]] || die '不接受非標準校驗路徑。'
    done < "$bundle_path/SHA256SUMS"
    [[ -z "$(find "$bundle_path/project" -type l -print -quit)" ]] || die '不接受含符號連結的搬移包。'
    (cd -- "$bundle_path" && sha256sum --check --strict SHA256SUMS)
}

mode="${1:-help}"
case "$mode" in
    help|-h|--help) usage; exit 0 ;;
    export|verify|import) ;;
    *) usage >&2; exit 2 ;;
esac
[[ $# -ge 2 ]] || { usage >&2; exit 2; }
bundle_arg="$2"

if [[ "$mode" == export ]]; then
    [[ $# -le 3 ]] || die 'export 參數過多。'
    with_checkpoint=true
    if [[ $# == 3 ]]; then
        [[ "$3" == --without-checkpoint ]] || die '未知的 export 選項。'
        with_checkpoint=false
    fi
    require_host
    image_platform="$(docker image inspect "$image_name" --format '{{.Os}}/{{.Architecture}}')"
    [[ "$image_platform" == linux/amd64 ]] || die "Image 平台不符：$image_platform"
    [[ ! -e "$bundle_arg" && ! -L "$bundle_arg" ]] || die '搬移包目錄已存在；請換新名稱，避免覆寫。'
    if "$with_checkpoint"; then
        [[ -f "$project_root/checkpoints/pi05_base/model.safetensors" &&
           -f "$project_root/checkpoints/pi05_base/config.json" ]] || die '缺少 pi05_base 權重；先 download 或加 --without-checkpoint。'
    fi

    # Copy only runtime/build inputs, not the full repository, Conda env or HF cache.
    files=(README.md Dockerfile .dockerignore docs/docker.md
        docker/run.sh docker/read_config.sh docker/migrate.sh docker/runtime.env.example
        docker/requirements.lock docker/verify.py docker/test_runner.py docker/test_migration.py
        policy/lerobot_observe.py policy/pi05_infer.py policy/pi05_infer_cpu.py
        policy/pi05_preflight.py policy/test_lerobot_integration.py
        policy/README_LEROBOT.md policy/CHECKPOINT_NOTES.md)
    for demo_path in "$project_root"/demos/python/*.py; do files+=("${demo_path#"$project_root/"}"); done
    for relative_path in "${files[@]}"; do
        [[ -f "$project_root/$relative_path" && ! -L "$project_root/$relative_path" ]] || die "缺少檔案或不接受符號連結：$relative_path"
    done
    mkdir -p -- "$bundle_arg"
    bundle_path="$(cd -- "$bundle_arg" && pwd)"
    mkdir -- "$bundle_path/project"
    (cd -- "$project_root" && cp --parents -- "${files[@]}" "$bundle_path/project/")

    # Save only portable robot/image settings, excluding machine-specific HF paths.
    printf 'ARM_IP=%s\nREALSENSE_SERIAL=%s\nTROSSEN_IMAGE=%s\n' \
        "${ARM_IP:-192.168.1.2}" "${REALSENSE_SERIAL:-261222076945}" "$image_name" \
        > "$bundle_path/project/docker/runtime.env"
    if "$with_checkpoint"; then
        printf '%s\n' '複製 pi05_base 權重（約 14.5 GB）…'
        mkdir -p -- "$bundle_path/project/checkpoints/pi05_base"
        for weight_path in "$project_root"/checkpoints/pi05_base/*.json \
                           "$project_root"/checkpoints/pi05_base/*.safetensors; do
            [[ -f "$weight_path" && ! -L "$weight_path" ]] || die "權重檔案不是一般檔案：$weight_path"
            cp --reflink=auto -- "$weight_path" "$bundle_path/project/checkpoints/pi05_base/"
        done
    fi
    docker image inspect "$image_name" --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Size}}' > "$bundle_path/image-info.txt"
    printf '%s\n' '匯出 Docker image；不包含帳號 token、HF cache 或 captures…'
    docker image save --output "$bundle_path/image.tar" "$image_name"
    printf '%s\n' '計算 SHA-256（大型檔案需要一些時間）…'
    (cd -- "$bundle_path" && {
        sha256sum image.tar image-info.txt
        find project -type f -print0 | sort -z | xargs -0 sha256sum
    } > SHA256SUMS)
    printf '搬移包完成：%s\n' "$bundle_path"
elif [[ "$mode" == verify ]]; then
    [[ $# == 2 ]] || die 'verify 參數過多。'
    verify_bundle "$bundle_arg"
else
    [[ $# == 3 ]] || { usage >&2; exit 2; }
    target_arg="$3"
    require_host
    [[ ! -e "$target_arg" && ! -L "$target_arg" ]] || die '目標專案已存在；請換新目錄，不會覆寫原本資料。'
    bundle_path="$(cd -- "$bundle_arg" && pwd)"
    verify_bundle "$bundle_path"
    # No hardware commands or policy inference during import.
    docker image load --input "$bundle_path/image.tar"
    read -r expected_id expected_platform image_size < "$bundle_path/image-info.txt"
    [[ "$expected_platform" == linux/amd64 ]] || die '搬移包平台不符。'
    docker image inspect "$expected_id" >/dev/null || die '載入的 image ID 與搬移包不符。'
    mkdir -p -- "$(dirname -- "$target_arg")"
    cp -a -- "$bundle_path/project" "$target_arg"
    printf '匯入完成：%s\n下一步：進入該目錄，執行 bash docker/run.sh check\n' "$target_arg"
fi
