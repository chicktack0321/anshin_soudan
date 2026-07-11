# ============================================================
# 日次自動実行スクリプト
# タスクスケジューラに登録して毎日決まった時間に実行する
#   例: 毎日 7:00 に実行
#   Register-ScheduledTask などの登録手順は README.md 参照
# ============================================================
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"   # ログの文字化け防止
Set-Location $PSScriptRoot

$logDir = Join-Path $PSScriptRoot "data\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("run_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

# VOICEVOXエンジンが起動していなければ起動を試みる
try {
    Invoke-RestMethod "http://127.0.0.1:50021/version" -TimeoutSec 3 | Out-Null
} catch {
    $vvPaths = @(
        "$env:LOCALAPPDATA\Programs\VOICEVOX\vv-engine\run.exe",
        "$env:LOCALAPPDATA\Programs\VOICEVOX\VOICEVOX.exe"
    )
    foreach ($p in $vvPaths) {
        if (Test-Path $p) {
            Start-Process $p
            Start-Sleep -Seconds 20   # エンジン起動待ち
            break
        }
    }
}

# パイプライン実行 (生成 → 投稿 → サイト更新)
python -m src.main run *>> $log
Get-Content $log -Tail 5
