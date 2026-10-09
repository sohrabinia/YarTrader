@echo off
setlocal
"C:\Projects\YarTrader\.venv\Scripts\python.exe" "C:\Projects\YarTrader\scripts\prune_artifact_store.py" --root "C:\YarTraderAI\Data\artifacts" --root "C:\Projects\YarTrader\storage\Data\artifacts" --manifest-root "C:\Projects\YarTrader\runtime_logs" --manifest-root "C:\Projects\YarTrader\storage" --manifest-root "C:\YarTraderAI" --keep-per-source 20 --unindexed-grace-hours 24 --apply --backup-dir "C:\Temp\YarTrader_artifact_gc_backup"
exit /b %ERRORLEVEL%
