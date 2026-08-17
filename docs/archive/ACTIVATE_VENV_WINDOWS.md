# How to Activate Virtual Environment on Windows

## The venv exists, but activation is failing. Try these solutions:

### Solution 1: Use Command Prompt (CMD) instead of PowerShell

1. **Open Command Prompt** (not PowerShell):
   - Press `Win + R`
   - Type: `cmd`
   - Press Enter

2. **Navigate to project:**
   ```cmd
   cd C:\Users\moeme\repos\tradingbuddy
   ```

3. **Activate venv:**
   ```cmd
   venv\Scripts\activate.bat
   ```

4. **You should see `(venv)` in your prompt**

### Solution 2: Use Full Path in PowerShell

```powershell
cd C:\Users\moeme\repos\tradingbuddy
& ".\venv\Scripts\Activate.ps1"
```

### Solution 3: Use Python Directly from venv

You can use Python from venv without activating:

```powershell
# Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Run backend
.\venv\Scripts\python.exe backend/main.py
```

### Solution 4: Fix PowerShell Execution Policy

If PowerShell blocks script execution:

1. **Open PowerShell as Administrator:**
   - Right-click Start menu
   - Select "Windows PowerShell (Admin)"

2. **Run:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Close and reopen VS Code terminal**

4. **Try activating again:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

### Solution 5: Recreate venv (if corrupted)

If venv seems corrupted, delete and recreate:

```powershell
# Delete old venv
Remove-Item -Recurse -Force venv

# Create new venv (try different Python commands)
python -m venv venv
# OR
python3 -m venv venv
# OR
py -m venv venv
# OR find Python and use full path:
C:\Python39\python.exe -m venv venv
```

### Solution 6: Use VS Code's Built-in Terminal

1. In VS Code, press `` Ctrl+` `` to open terminal
2. VS Code should auto-activate venv if configured correctly
3. Check bottom-right corner for Python interpreter selection

## Quick Test - Use venv Python Directly

**You don't need to activate venv to use it!**

```powershell
# Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Run backend
.\venv\Scripts\python.exe backend/main.py
```

This works even if activation fails!

## VS Code Python Interpreter

1. Press `Ctrl+Shift+P`
2. Type: "Python: Select Interpreter"
3. Choose: `.\venv\Scripts\python.exe`
4. VS Code will use this automatically

## Recommended: Use Command Prompt

**Easiest solution - switch to CMD:**

1. In VS Code, click terminal dropdown (top-right of terminal)
2. Select "Command Prompt" instead of PowerShell
3. Run:
   ```cmd
   cd C:\Users\moeme\repos\tradingbuddy
   venv\Scripts\activate.bat
   ```

You should see `(venv)` in the prompt!























