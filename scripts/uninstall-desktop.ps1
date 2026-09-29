$ErrorActionPreference = 'Stop'
$local = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' }
$programs = [IO.Path]::GetFullPath((Join-Path $local 'Programs'))
$install = [IO.Path]::GetFullPath((Join-Path $programs 'GenshinPlanner'))
if (-not $install.StartsWith($programs + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $install) -ne 'GenshinPlanner' -or (Split-Path -Parent $install) -ne $programs) {
    throw 'Refusing to remove an unexpected installation path.'
}
if (-not (Test-Path -LiteralPath (Join-Path $install 'GenshinPlanner.exe') -PathType Leaf)) {
    throw 'The expected Genshin Planner installation was not found.'
}
if (Get-Process -Name 'GenshinPlanner' -ErrorAction SilentlyContinue) {
    throw 'Hãy đóng Genshin Planner trước khi gỡ cài đặt.'
}
$answer = Read-Host 'Gỡ app? Database, snapshot và backup trong LocalAppData sẽ được giữ nguyên. (y/N)'
if ($answer -notin @('y', 'Y')) { exit 0 }
$shortcutFolder = Join-Path $local 'Microsoft\Windows\Start Menu\Programs\Genshin Planner'
if (Test-Path -LiteralPath $shortcutFolder) { Remove-Item -LiteralPath $shortcutFolder -Recurse -Force }
Remove-Item -LiteralPath $install -Recurse -Force
Write-Host 'Đã gỡ ứng dụng. Dữ liệu account được giữ nguyên.'
