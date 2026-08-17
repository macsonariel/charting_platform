# Quick Start - Windows (Python Not Found Fix)

## If `python` command doesn't work, use `py`:

### 1. Create Virtual Environment
```powershell
py -m venv venv
```

### 2. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

**If you get execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Dependencies
```powershell
py -m pip install -r requirements.txt
```

### 4. Run Backend
```powershell
py backend/main.py
```

## Alternative: Use Command Prompt (CMD)

If PowerShell gives issues, use Command Prompt:

```cmd
python -m venv venv
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python backend/main.py
```

## Check Which Python Commands Work

Try these in order:

```powershell
py --version          # Usually works on Windows
python3 --version     # Sometimes works
python --version      # Rarely works on Windows
```

**Use whichever one shows a version number!**

## VS Code Setup

1. Press `Ctrl+Shift+P`
2. Type: "Python: Select Interpreter"
3. Choose: `.\venv\Scripts\python.exe` (after creating venv)

## Still Not Working?

1. **Install Python**: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Restart VS Code after installation

2. **Or use Anaconda**:
   ```powershell
   conda create -n tradingbuddy python=3.9
   conda activate tradingbuddy
   pip install -r requirements.txt
   python backend/main.py
   ```























