# VS Code Setup Guide for Trading Buddy

Complete guide to set up and run Trading Buddy in Visual Studio Code.

## Prerequisites

1. **Python 3.8+** installed
2. **VS Code** installed
3. **Git** (optional, for version control)

## Step 1: Open Project in VS Code

1. Open VS Code
2. Click **File → Open Folder**
3. Navigate to your `tradingbuddy` folder
4. Click **Select Folder**

## Step 2: Set Up Python Environment

### Option A: Using VS Code's Built-in Terminal

1. Open terminal in VS Code: **Terminal → New Terminal** (or `Ctrl+`` `)

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Option B: Using VS Code Python Extension

1. Install **Python extension** (if not already installed):
   - Press `Ctrl+Shift+X` (or `Cmd+Shift+X` on Mac)
   - Search for "Python" by Microsoft
   - Click Install

2. Select Python interpreter:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Python: Select Interpreter"
   - Choose your Python version

3. VS Code will detect `requirements.txt` and suggest installing dependencies

## Step 3: Configure VS Code Settings

### Create `.vscode/settings.json`

Create a folder `.vscode` in your project root, then create `settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    },
    "python.envFile": "${workspaceFolder}/.env"
}
```

### Create `.vscode/launch.json` (for debugging)

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI Backend",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/main.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "justMyCode": true
        }
    ]
}
```

## Step 4: Run the Backend

### Method 1: Using VS Code Terminal

1. Open terminal: **Terminal → New Terminal**
2. Make sure virtual environment is activated (you should see `(venv)` in prompt)
3. Run:
   ```bash
   python backend/main.py
   ```
4. You should see:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

### Method 2: Using VS Code Debugger

1. Press `F5` or click **Run → Start Debugging**
2. Select "Python: FastAPI Backend" configuration
3. Backend will start with debugging enabled
4. Set breakpoints by clicking left of line numbers

### Method 3: Using VS Code Tasks

Create `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Backend",
            "type": "shell",
            "command": "python",
            "args": ["backend/main.py"],
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": [],
            "presentation": {
                "reveal": "always",
                "panel": "new"
            },
            "group": {
                "kind": "build",
                "isDefault": true
            }
        }
    ]
}
```

Then press `Ctrl+Shift+B` to run the task.

## Step 5: Open Frontend

1. **Right-click** on `html/dashboard/index.html`
2. Select **"Open with Live Server"** (if you have Live Server extension)
   
   OR
   
3. **Right-click** on `html/dashboard/index.html`
4. Select **"Copy Path"**
5. Open browser and paste path, or use:
   ```
   file:///C:/Users/moeme/repos/tradingbuddy/html/dashboard/index.html
   ```

## Step 6: Recommended VS Code Extensions

Install these extensions for better development experience:

1. **Python** (Microsoft) - Python language support
2. **Pylance** (Microsoft) - Fast Python language server
3. **Live Server** (Ritwick Dey) - Auto-reload HTML files
4. **Prettier** - Code formatter
5. **ESLint** - JavaScript linting
6. **GitLens** - Git supercharged
7. **Thunder Client** - API testing (alternative to Postman)

### Install Extensions:

1. Press `Ctrl+Shift+X`
2. Search for extension name
3. Click **Install**

## Step 7: Environment Variables (Optional)

Create `.env` file in project root:

```env
DATA_SOURCE=dummy
TWELVEDATA_API_KEY=your_key_here
```

VS Code will automatically load this file if you have Python extension installed.

## Step 8: Testing the Setup

### Test Backend:

1. Start backend (see Step 4)
2. Open browser: `http://localhost:8000`
3. You should see API welcome message
4. Test endpoint: `http://localhost:8000/api/chart/highs-lows?symbol=XAUUSD`

### Test Frontend:

1. Open `html/dashboard/index.html` in browser
2. Chart should load
3. Check browser console (F12) for any errors
4. Lines should appear after a few seconds

## VS Code Tips

### 1. Multi-Terminal Setup

Open multiple terminals for backend and frontend:

1. **Terminal 1**: Backend
   ```bash
   python backend/main.py
   ```

2. **Terminal 2**: Frontend (if using Live Server)
   - Right-click HTML file → "Open with Live Server"

### 2. Debugging Python

1. Set breakpoint: Click left of line number (red dot appears)
2. Press `F5` to start debugging
3. Use debug panel:
   - **Variables**: See variable values
   - **Watch**: Monitor specific expressions
   - **Call Stack**: See function call hierarchy
   - **Debug Console**: Execute Python code

### 3. Code Navigation

- **Go to Definition**: `F12` or `Ctrl+Click`
- **Find References**: `Shift+F12`
- **Go to Symbol**: `Ctrl+Shift+O`
- **Quick Open**: `Ctrl+P`

### 4. Integrated Terminal Shortcuts

- **New Terminal**: `Ctrl+Shift+`` ` (backtick)
- **Split Terminal**: `Ctrl+\`
- **Kill Terminal**: `Ctrl+Shift+`` ` then `Ctrl+C`

### 5. File Explorer

- **New File**: Right-click folder → "New File"
- **New Folder**: Right-click → "New Folder"
- **Reveal in File Explorer**: Right-click file → "Reveal in File Explorer"

## Troubleshooting

### Backend won't start

1. **Check Python version:**
   ```bash
   python --version
   ```
   Should be 3.8+

2. **Check dependencies:**
   ```bash
   pip list
   ```
   Should show fastapi, uvicorn, etc.

3. **Check port 8000:**
   ```bash
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Mac/Linux
   ```
   If port is in use, change port in `backend/main.py`:
   ```python
   uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

### Frontend can't connect to backend

1. **Check backend is running**: Visit `http://localhost:8000`
2. **Check CORS**: Backend should allow all origins (already configured)
3. **Check browser console**: Look for CORS or connection errors
4. **Check API URL**: Should be `http://localhost:8000` in `chart_lines.js`

### Python imports not working

1. **Check PYTHONPATH**: Should include project root
2. **Check virtual environment**: Make sure it's activated
3. **Restart VS Code**: Sometimes needed after installing packages

## Quick Start Checklist

- [ ] Open project in VS Code
- [ ] Create virtual environment (`python -m venv venv`)
- [ ] Activate virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Start backend (`python backend/main.py`)
- [ ] Open `html/dashboard/index.html` in browser
- [ ] Verify chart loads and lines appear

## Next Steps

1. **Add real data source**: Set `DATA_SOURCE` environment variable
2. **Customize analysis**: Modify `backend/api/chart_analysis.py`
3. **Add features**: Extend frontend in `script/dashboard/`
4. **Debug issues**: Use VS Code debugger (F5)

## Useful VS Code Keyboard Shortcuts

| Action | Windows/Linux | Mac |
|--------|--------------|-----|
| Command Palette | `Ctrl+Shift+P` | `Cmd+Shift+P` |
| New Terminal | `Ctrl+Shift+`` ` | `Cmd+Shift+`` ` |
| Find in Files | `Ctrl+Shift+F` | `Cmd+Shift+F` |
| Go to Line | `Ctrl+G` | `Cmd+G` |
| Toggle Sidebar | `Ctrl+B` | `Cmd+B` |
| Toggle Terminal | `Ctrl+`` ` | `Cmd+`` ` |
| Format Document | `Shift+Alt+F` | `Shift+Option+F` |
| Start Debugging | `F5` | `F5` |

Happy coding! 🚀






















