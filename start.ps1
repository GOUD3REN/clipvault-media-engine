$bin = "C:\Users\PC\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
$env:CLIPVAULT_FFMPEG = "$bin\ffmpeg.exe"
$env:CLIPVAULT_FFPROBE = "$bin\ffprobe.exe"
& "c:\Users\PC\Documents\anotacoes\visual code\.venv\Scripts\Activate.ps1"
Set-Location "C:\Users\PC\Documents\anotacoes\visual code\clipvault-media-engine"
python run.py