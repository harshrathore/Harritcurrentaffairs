$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\ratho\Desktop\HarritNewsEngine\activator\gdrive_autoupload.py" -WorkingDirectory "C:\Users\ratho\Desktop\HarritNewsEngine\activator"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName "GDriveAutoUpload" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Auto upload slides to Google Drive on login"

Write-Host "Task registered successfully!"
Write-Host "The script will start automatically when you log in."
Write-Host "It checks for new slides every 60 seconds."
