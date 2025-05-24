@echo off
set /p commitMessage="上传信息: "

git add .
git commit -m "%commitMessage%"
git push

if %errorlevel% neq 0 (
    echo "Git operation failed. Please check for errors."
) else (
    echo "Git operation successful."
)

pause
