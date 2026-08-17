# Windows Setup Guide - Trading Buddy

## Python Not Recognized? Try These Solutions

### Solution 1: Use `py` instead of `python`

On Windows, Python is often installed as `py` launcher:

```powershell
# Try this instead:
py -m venv venv

# Then activate:
.\venv\Scripts\Activate.ps1

# Install dependencies:
py -m pip install -r requirements.txt

# Run backend:
py backend/main.py
```

### Solution 2: Check if Python is Installed

1. **Check Python version:**
   ```powershell
   py --version
   ```
   OR
   ```powershell
   python3 --version
   ```

2. **If nothing works, Python might not be installed:**
   - Download from: https://www.python.org/downloads/
   - **IMPORTANT**: Check "Add Python to PATH" during installation
   - Restart VS Code after installation

### Solution 3: Find Python Installation

1. **Search for Python:**
   ```powershell
   where python
   where py
   where python3
   ```

2. **Common Python locations:**
   - `C:\Python39\python.exe`
   - `C:\Users\YourName\AppData\Local\Programs\Python\Python39\python.exe`
   - `C:\Program Files\Python39\python.exe`

### Solution 4: Add Python to PATH (Manual)

If Python is installed but not in PATH:

1. **Find Python installation:**
   - Usually in: `C:\Users\YourName\AppData\Local\Programs\Python\`

2. **Add to PATH:**
   - Press `Win + X` → System → Advanced system settings
   - Click "Environment Variables"
   - Under "User variables", find "Path"
   - Click "Edit" → "New"
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python39\`
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python39\Scripts\`
   - Click OK on all dialogs
   - **Restart VS Code**

### Solution 5: Use Python from Microsoft Store

If you have Python from Microsoft Store:

```powershell
python3 -m venv venv
.\venv\Scripts\Activate.ps1
python3 -m pip install -r requirements.txt
python3 backend/main.py
```

## Quick Setup Steps (Windows)

### Step 1: Verify Python Installation

```powershell
# Try each of these:
py --version
python3 --version
python --version
```

**Use whichever command works!**

### Step 2: Create Virtual Environment

```powershell
# Use the command that worked in Step 1:
py -m venv venv
# OR
python3 -m venv venv
# OR
python -m venv venv
```

### Step 3: Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an execution policy error:**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again.

### Step 4: Install Dependencies

```powershell
# Use the same Python command from Step 1:
py -m pip install -r requirements.txt
# OR
python3 -m pip install -r requirements.txt
```

### Step 5: Run Backend

```powershell
py backend/main.py
# OR
python3 backend/main.py
```

## VS Code Python Interpreter Selection

1. Press `Ctrl+Shift+P`
2. Type: "Python: Select Interpreter"
3. Choose the Python version you found
4. If you see multiple, choose the one in your `venv` folder:
   - `.\venv\Scripts\python.exe`

## Alternative: Use Anaconda/Miniconda

If you have Anaconda installed:

```powershell
# Create environment
conda create -n tradingbuddy python=3.9
conda activate tradingbuddy

# Install dependencies
pip install -r requirements.txt

# Run backend
python backend/main.py
```

## Troubleshooting PowerShell Execution Policy

If you see: "cannot be loaded because running scripts is disabled"

```powershell
# Run as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Quick Test

After setup, test if everything works:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Check Python
py --version

# Check pip
py -m pip --version

# Install dependencies
py -m pip install -r requirements.txt

# Test import
py -c "import fastapi; print('FastAPI installed!')"

# Run backend
py backend/main.py
```

You should see: `INFO: Uvicorn running on http://0.0.0.0:8000`

## Still Having Issues?

1. **Restart VS Code** after installing Python
2. **Restart your computer** after adding Python to PATH
3. **Use Command Prompt** instead of PowerShell:
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
4. **Check Python installation:**
   - Open Command Prompt
   - Type: `where python`
   - If nothing shows, Python is not in PATH























