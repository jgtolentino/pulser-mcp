const { app, BrowserWindow, Menu, Tray, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const AutoLaunch = require('auto-launch');
const Store = require('electron-store');
const notifier = require('node-notifier');

// Configuration
const isDev = process.env.NODE_ENV === 'development';
const store = new Store();

class MCPDesktopApp {
  constructor() {
    this.mainWindow = null;
    this.tray = null;
    this.mcpServer = null;
    this.corsProxy = null;
    this.autoLauncher = null;
    
    this.config = {
      mcpPort: store.get('mcpPort', 8000),
      corsPort: store.get('corsPort', 8001),
      autoStart: store.get('autoStart', true),
      minimizeToTray: store.get('minimizeToTray', true),
      notifications: store.get('notifications', true)
    };
  }

  async initialize() {
    await app.whenReady();
    
    // Set up auto-launcher
    this.autoLauncher = new AutoLaunch({
      name: 'MCP Complete Server',
      path: app.getPath('exe')
    });

    // Apply auto-start setting
    if (this.config.autoStart) {
      await this.autoLauncher.enable();
    }

    this.createWindow();
    this.createTray();
    this.setupEventHandlers();
    this.startMCPServer();
    
    // Show notification
    if (this.config.notifications) {
      notifier.notify({
        title: 'MCP Complete Server',
        message: 'Desktop application started successfully',
        icon: this.getIconPath()
      });
    }
  }

  createWindow() {
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 800,
      minHeight: 600,
      icon: this.getIconPath(),
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
        enableRemoteModule: true
      },
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      show: false
    });

    // Load the UI
    this.mainWindow.loadFile(path.join(__dirname, 'ui', 'index.html'));

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      
      if (isDev) {
        this.mainWindow.webContents.openDevTools();
      }
    });

    // Handle window close
    this.mainWindow.on('close', (event) => {
      if (this.config.minimizeToTray && !app.isQuiting) {
        event.preventDefault();
        this.mainWindow.hide();
        
        if (this.config.notifications) {
          notifier.notify({
            title: 'MCP Complete Server',
            message: 'App minimized to system tray',
            icon: this.getIconPath()
          });
        }
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });
  }

  createTray() {
    this.tray = new Tray(this.getIconPath());
    
    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'MCP Complete Server',
        type: 'normal',
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Show Window',
        click: () => {
          if (this.mainWindow) {
            this.mainWindow.show();
            this.mainWindow.focus();
          }
        }
      },
      {
        label: 'Server Status',
        click: () => this.checkServerStatus()
      },
      { type: 'separator' },
      {
        label: 'Open in Browser',
        click: () => shell.openExternal(`http://localhost:${this.config.mcpPort}`)
      },
      {
        label: 'View Logs',
        click: () => this.openLogsFolder()
      },
      { type: 'separator' },
      {
        label: 'Restart Server',
        click: () => this.restartMCPServer()
      },
      {
        label: 'Settings',
        click: () => this.showSettings()
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          app.isQuiting = true;
          this.stopMCPServer();
          app.quit();
        }
      }
    ]);

    this.tray.setContextMenu(contextMenu);
    this.tray.setToolTip('MCP Complete Server');

    // Double-click to show window
    this.tray.on('double-click', () => {
      if (this.mainWindow) {
        this.mainWindow.show();
        this.mainWindow.focus();
      }
    });
  }

  setupEventHandlers() {
    // IPC handlers for renderer process
    ipcMain.handle('get-server-status', () => this.getServerStatus());
    ipcMain.handle('restart-server', () => this.restartMCPServer());
    ipcMain.handle('stop-server', () => this.stopMCPServer());
    ipcMain.handle('start-server', () => this.startMCPServer());
    ipcMain.handle('get-config', () => this.config);
    ipcMain.handle('update-config', (event, newConfig) => this.updateConfig(newConfig));
    ipcMain.handle('get-logs', () => this.getLogs());
    ipcMain.handle('open-logs-folder', () => this.openLogsFolder());
    ipcMain.handle('open-browser', () => shell.openExternal(`http://localhost:${this.config.mcpPort}`));

    // App event handlers
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin' && !this.config.minimizeToTray) {
        this.stopMCPServer();
        app.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createWindow();
      }
    });

    app.on('before-quit', () => {
      app.isQuiting = true;
      this.stopMCPServer();
    });
  }

  getServerPath() {
    if (isDev) {
      return path.join(__dirname, '..', '..', '..', 'src');
    } else {
      return path.join(process.resourcesPath, 'server', 'src');
    }
  }

  async startMCPServer() {
    try {
      const serverPath = this.getServerPath();
      const serverScript = path.join(serverPath, 'server.js');
      const proxyScript = path.join(serverPath, 'cors-proxy.js');

      // Start main MCP server
      this.mcpServer = spawn('node', [serverScript], {
        cwd: path.dirname(serverPath),
        env: {
          ...process.env,
          MCP_PORT: this.config.mcpPort,
          NODE_ENV: 'production'
        },
        stdio: ['pipe', 'pipe', 'pipe']
      });

      // Start CORS proxy
      this.corsProxy = spawn('node', [proxyScript], {
        cwd: path.dirname(serverPath),
        env: {
          ...process.env,
          CORS_PORT: this.config.corsPort,
          MCP_PORT: this.config.mcpPort,
          NODE_ENV: 'production'
        },
        stdio: ['pipe', 'pipe', 'pipe']
      });

      // Handle server events
      this.mcpServer.on('error', (error) => {
        console.error('MCP Server error:', error);
        this.showErrorNotification('MCP Server failed to start', error.message);
      });

      this.corsProxy.on('error', (error) => {
        console.error('CORS Proxy error:', error);
        this.showErrorNotification('CORS Proxy failed to start', error.message);
      });

      // Wait for servers to start
      await this.waitForServer();
      
      if (this.config.notifications) {
        notifier.notify({
          title: 'MCP Complete Server',
          message: 'Servers started successfully',
          icon: this.getIconPath()
        });
      }

      // Update tray tooltip
      this.tray.setToolTip(`MCP Server: Running (Port ${this.config.mcpPort})`);

    } catch (error) {
      console.error('Failed to start MCP server:', error);
      this.showErrorNotification('Server Start Failed', error.message);
    }
  }

  async waitForServer() {
    return new Promise((resolve, reject) => {
      const checkServer = () => {
        exec(`curl -s http://localhost:${this.config.mcpPort}/health`, (error, stdout) => {
          if (error) {
            setTimeout(checkServer, 1000);
          } else {
            resolve();
          }
        });
      };
      
      setTimeout(checkServer, 2000);
      setTimeout(() => reject(new Error('Server start timeout')), 30000);
    });
  }

  stopMCPServer() {
    if (this.mcpServer) {
      this.mcpServer.kill();
      this.mcpServer = null;
    }

    if (this.corsProxy) {
      this.corsProxy.kill();
      this.corsProxy = null;
    }

    this.tray.setToolTip('MCP Server: Stopped');
  }

  async restartMCPServer() {
    this.stopMCPServer();
    await new Promise(resolve => setTimeout(resolve, 2000));
    await this.startMCPServer();
  }

  async getServerStatus() {
    try {
      const response = await fetch(`http://localhost:${this.config.mcpPort}/health`);
      const data = await response.json();
      return {
        running: true,
        status: data.status,
        timestamp: data.timestamp,
        port: this.config.mcpPort,
        corsPort: this.config.corsPort
      };
    } catch (error) {
      return {
        running: false,
        error: error.message,
        port: this.config.mcpPort,
        corsPort: this.config.corsPort
      };
    }
  }

  async checkServerStatus() {
    const status = await this.getServerStatus();
    
    dialog.showMessageBox(this.mainWindow, {
      type: status.running ? 'info' : 'error',
      title: 'Server Status',
      message: status.running 
        ? `MCP Server is running on port ${status.port}\\nCORS Proxy on port ${status.corsPort}\\nStatus: ${status.status}`
        : `MCP Server is not running\\nError: ${status.error || 'Unknown'}`
    });
  }

  async updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
    
    // Save to store
    Object.keys(newConfig).forEach(key => {
      store.set(key, newConfig[key]);
    });

    // Apply auto-start setting
    if (newConfig.autoStart !== undefined) {
      if (newConfig.autoStart) {
        await this.autoLauncher.enable();
      } else {
        await this.autoLauncher.disable();
      }
    }

    // Restart server if port changed
    if (newConfig.mcpPort || newConfig.corsPort) {
      await this.restartMCPServer();
    }
  }

  getLogs() {
    try {
      const logsPath = path.join(this.getServerPath(), '..', 'logs');
      const serverLog = path.join(logsPath, 'combined.log');
      const errorLog = path.join(logsPath, 'error.log');
      
      let logs = '';
      
      if (fs.existsSync(serverLog)) {
        logs += '=== Server Logs ===\\n';
        logs += fs.readFileSync(serverLog, 'utf8').split('\\n').slice(-50).join('\\n');
      }
      
      if (fs.existsSync(errorLog)) {
        logs += '\\n\\n=== Error Logs ===\\n';
        logs += fs.readFileSync(errorLog, 'utf8').split('\\n').slice(-20).join('\\n');
      }
      
      return logs || 'No logs available';
    } catch (error) {
      return `Error reading logs: ${error.message}`;
    }
  }

  openLogsFolder() {
    const logsPath = path.join(this.getServerPath(), '..', 'logs');
    shell.openPath(logsPath);
  }

  showSettings() {
    if (this.mainWindow) {
      this.mainWindow.show();
      this.mainWindow.focus();
      this.mainWindow.webContents.send('show-settings');
    }
  }

  showErrorNotification(title, message) {
    if (this.config.notifications) {
      notifier.notify({
        title,
        message,
        icon: this.getIconPath(),
        sound: true
      });
    }

    dialog.showErrorBox(title, message);
  }

  getIconPath() {
    return path.join(__dirname, '..', 'assets', 'icon.png');
  }
}

// Initialize the app
const mcpApp = new MCPDesktopApp();
mcpApp.initialize().catch(console.error);

// Handle protocol for deep linking
app.setAsDefaultProtocolClient('mcp-complete');
