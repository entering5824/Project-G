$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'GenshinPlanner'
$sourceExe = Join-Path $package 'GenshinPlanner.exe'
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    throw 'Không tìm thấy GenshinPlanner.exe trong gói phát hành. Hãy giải nén đầy đủ thư mục GenshinPlanner.'
}

$running = Get-Process -Name 'GenshinPlanner' -ErrorAction SilentlyContinue
if ($running) {
    throw 'Hãy đóng Genshin Planner trước khi cài hoặc cập nhật.'
}

$local = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' }
$programs = [IO.Path]::GetFullPath((Join-Path $local 'Programs'))
$destination = [IO.Path]::GetFullPath((Join-Path $programs 'GenshinPlanner'))
if (-not $destination.StartsWith($programs + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Install path is outside the per-user Programs folder.'
}

New-Item -ItemType Directory -Path $programs -Force | Out-Null
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item -Path (Join-Path $package '*') -Destination $destination -Recurse -Force

$startMenu = Join-Path $local 'Microsoft\Windows\Start Menu\Programs\Genshin Planner'
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $startMenu 'Genshin Planner.lnk'
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $destination 'GenshinPlanner.exe'
$shortcut.WorkingDirectory = $destination
$shortcut.Description = 'Genshin Account Progression Planner'
$shortcut.Save()
$uninstall = $shell.CreateShortcut((Join-Path $startMenu 'Uninstall Genshin Planner.lnk'))
$uninstall.TargetPath = Join-Path $destination 'Uninstall-GenshinPlanner.bat'
$uninstall.WorkingDirectory = $destination
$uninstall.Description = 'Remove Genshin Planner; keep account data'
$uninstall.Save()

Write-Host 'Đã cài Genshin Planner và tạo shortcut trong Start Menu.'
Write-Host "Dữ liệu account vẫn ở: $(Join-Path $local 'GenshinPlanner')"
