on run
	set appRoot to POSIX path of (path to me)
	set launcherPath to appRoot & "Contents/Resources/workbench/start-online.command"
	set logPath to "$HOME/.yanru-video-agent/desktop-launcher.log"
	do shell script "/bin/mkdir -p $HOME/.yanru-video-agent && /usr/bin/nohup /bin/zsh " & quoted form of launcherPath & " >" & logPath & " 2>&1 &"
end run
