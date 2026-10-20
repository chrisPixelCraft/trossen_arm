#!/usr/bin/env bash
# Parse data only: never source/eval user configuration.
load_runtime_config() {
    local config_path="$1" config_line config_key config_value line_number=0
    [[ -f "$config_path" ]] || return 0
    while IFS= read -r config_line || [[ -n "$config_line" ]]; do
        line_number=$((line_number + 1))
        config_line="${config_line%$'\r'}"
        [[ "$config_line" =~ ^[[:space:]]*$ || "$config_line" =~ ^[[:space:]]*# ]] && continue
        if [[ "$config_line" != *=* ]]; then
            printf '設定格式錯誤：%s:%s（請用 KEY=VALUE）\n' "$config_path" "$line_number" >&2
            return 2
        fi
        config_key="${config_line%%=*}"
        config_value="${config_line#*=}"
        case "$config_key" in
            ARM_IP|REALSENSE_SERIAL|TROSSEN_IMAGE|HF_CACHE_DIR) ;;
            *) printf '不支援的設定：%s:%s\n' "$config_path" "$line_number" >&2; return 2 ;;
        esac
        if [[ "$config_value" == \"* || "$config_value" == \'* ]]; then
            printf '設定值不需引號：%s:%s\n' "$config_path" "$line_number" >&2
            return 2
        fi
        # An explicit environment variable takes priority over the file.
        if [[ ! -v "$config_key" ]]; then
            printf -v "$config_key" '%s' "$config_value"
            export "$config_key"
        fi
    done < "$config_path"
}
