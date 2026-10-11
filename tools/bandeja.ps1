# Beatloom na bandeja do Windows: sobe o servidor escondido e deixa um icone perto do relogio (duplo clique abre a pagina, "Sair" encerra).
# Beatloom in the Windows tray: starts the server hidden and leaves an icon near the clock (double-click opens the page, "Quit" stops it).
# Nao instala nada: usa o PowerShell e o .NET que o Windows ja tem. Chamado por `start.bat bandeja`.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$script:porta = if ($env:BEATLOOM_PORTA) { [int]$env:BEATLOOM_PORTA } else { 8777 }  # so os testes mudam
$pagina = "http://localhost:$script:porta"

$en = $false
try { $en = (Get-Content "$raiz\beatloom.json" -Raw -Encoding UTF8 | ConvertFrom-Json).lingua -eq "en" } catch {}
$frase = if ($en) { @{ abrir = "Open Beatloom"; sair = "Quit"; rodando = "Beatloom is running here. Double-click to open." } }
         else { @{ abrir = "Abrir o Beatloom"; sair = "Sair"; rodando = "O Beatloom esta rodando aqui. Duplo clique para abrir." } }

# ja tem um Beatloom aberto nessa porta: so abre a pagina
$tcp = New-Object System.Net.Sockets.TcpClient
try { $tcp.Connect("127.0.0.1", $script:porta); $tcp.Close(); Start-Process $pagina; exit 0 } catch {}

New-Item -ItemType Directory -Force "$raiz\logs" | Out-Null
$script:srv = Start-Process "$raiz\.venv\Scripts\python.exe" -ArgumentList "-u", "app.py", "--sem-navegador" -WorkingDirectory $raiz -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$raiz\logs\beatloom.log" -RedirectStandardError "$raiz\logs\beatloom.err.log"

$icone = New-Object System.Windows.Forms.NotifyIcon
$icone.Icon = New-Object System.Drawing.Icon("$raiz\installer\beatloom.ico")
$icone.Text = "Beatloom"
$menu = New-Object System.Windows.Forms.ContextMenuStrip
$menu.Items.Add($frase.abrir).Add_Click({ Start-Process $pagina }) | Out-Null
$menu.Items.Add($frase.sair).Add_Click({ [System.Windows.Forms.Application]::Exit() }) | Out-Null
$icone.ContextMenuStrip = $menu
$icone.Add_DoubleClick({ Start-Process $pagina })
$icone.Visible = $true
$icone.ShowBalloonTip(4000, "Beatloom", $frase.rodando, [System.Windows.Forms.ToolTipIcon]::Info)

# se o servidor cair (ou ja houver outro), o icone some sozinho
$relogio = New-Object System.Windows.Forms.Timer
$relogio.Interval = 3000
$relogio.Add_Tick({ if ($script:srv.HasExited) { [System.Windows.Forms.Application]::Exit() } })
$relogio.Start()
[System.Windows.Forms.Application]::Run()

$icone.Visible = $false
$icone.Dispose()
if (-not $script:srv.HasExited) { & taskkill /T /F /PID $script:srv.Id | Out-Null }  # a fila fica guardada em .cache\fila.json e volta na proxima vez
