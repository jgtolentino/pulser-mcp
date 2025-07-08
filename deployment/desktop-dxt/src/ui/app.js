const { ipcRenderer } = require('electron');

class MCPDesktopUI {
    constructor() {
        this.currentTab = 'dashboard';
        this.refreshInterval = null;
        this.serverStatus = null;
        
        this.toolParameters = {
            sqlite_get: [
                { name: 'key', type: 'text', required: true, description: 'Key to retrieve' }
            ],
            sqlite_set: [
                { name: 'key', type: 'text', required: true, description: 'Key to store' },
                { name: 'value', type: 'text', required: true, description: 'Value to store' },
                { name: 'type', type: 'text', required: false, description: 'Data type (string, number, json)', default: 'string' }
            ],
            sqlite_delete: [
                { name: 'key', type: 'text', required: true, description: 'Key to delete' }
            ],
            sqlite_query: [
                { name: 'query', type: 'textarea', required: true, description: 'SQL query to execute' },
                { name: 'params', type: 'textarea', required: false, description: 'Query parameters (JSON array)' }
            ],
            sqlite_list: [
                { name: 'pattern', type: 'text', required: false, description: 'Pattern to match (% wildcards)', default: '%' },
                { name: 'limit', type: 'number', required: false, description: 'Maximum results', default: 100 },
                { name: 'offset', type: 'number', required: false, description: 'Results offset', default: 0 }
            ],
            get_logs: [
                { name: 'level', type: 'select', required: false, description: 'Log level filter', options: ['', 'error', 'warn', 'info', 'debug'] },
                { name: 'limit', type: 'number', required: false, description: 'Maximum results', default: 50 },
                { name: 'offset', type: 'number', required: false, description: 'Results offset', default: 0 }
            ]
        };
    }

    async initialize() {
        this.setupEventListeners();
        this.setupTabNavigation();
        this.setupToolInterface();
        this.loadSettings();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Initial data load
        await this.refreshDashboard();
        
        // Listen for main process events
        ipcRenderer.on('show-settings', () => {
            this.switchTab('settings');
        });
    }

    setupEventListeners() {
        // Header actions
        document.getElementById('refresh-btn').addEventListener('click', () => this.refreshDashboard());
        document.getElementById('settings-btn').addEventListener('click', () => this.switchTab('settings'));

        // Dashboard actions
        document.getElementById('restart-server-btn').addEventListener('click', () => this.restartServer());
        document.getElementById('open-browser-btn').addEventListener('click', () => this.openBrowser());
        document.getElementById('test-proxy-btn').addEventListener('click', () => this.testProxy());
        document.getElementById('test-connection-btn').addEventListener('click', () => this.testConnection());
        document.getElementById('view-logs-btn').addEventListener('click', () => this.switchTab('logs'));
        document.getElementById('open-logs-folder-btn').addEventListener('click', () => this.openLogsFolder());
        document.getElementById('copy-urls-btn').addEventListener('click', () => this.copyUrls());

        // Tools actions
        document.getElementById('tool-select').addEventListener('change', () => this.updateToolParameters());
        document.getElementById('execute-tool-btn').addEventListener('click', () => this.executeTool());

        // Logs actions
        document.getElementById('refresh-logs-btn').addEventListener('click', () => this.refreshLogs());
        document.getElementById('clear-logs-btn').addEventListener('click', () => this.clearLogs());
        document.getElementById('export-logs-btn').addEventListener('click', () => this.exportLogs());

        // Settings actions
        document.getElementById('save-settings-btn').addEventListener('click', () => this.saveSettings());
        document.getElementById('reset-settings-btn').addEventListener('click', () => this.resetSettings());

        // Integration actions
        document.getElementById('verify-server-btn').addEventListener('click', () => this.verifyServer());
        document.getElementById('test-tools-btn').addEventListener('click', () => this.testTools());
        document.getElementById('open-claude-btn').addEventListener('click', () => this.openClaude());

        // Copy buttons
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.copyToClipboard(e.target));
        });
    }

    setupTabNavigation() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });
    }

    setupToolInterface() {
        this.updateToolParameters();
    }

    switchTab(tabName) {
        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        if (tabName === 'logs') {
            this.refreshLogs();
        } else if (tabName === 'settings') {
            this.loadSettings();
        }
    }

    async refreshDashboard() {
        try {
            this.serverStatus = await ipcRenderer.invoke('get-server-status');
            this.updateDashboardUI();
        } catch (error) {
            this.showToast('Failed to refresh dashboard', 'error');
        }
    }

    updateDashboardUI() {
        if (!this.serverStatus) return;

        // Update server status
        const serverStatusEl = document.getElementById('server-status');
        const serverStatusTextEl = document.getElementById('server-status-text');
        const serverPortEl = document.getElementById('server-port');

        if (this.serverStatus.running) {
            serverStatusEl.className = 'status-indicator status-running';
            serverStatusTextEl.textContent = this.serverStatus.status || 'Running';
        } else {
            serverStatusEl.className = 'status-indicator status-stopped';
            serverStatusTextEl.textContent = 'Stopped';
        }

        serverPortEl.textContent = this.serverStatus.port;

        // Update proxy status
        const proxyStatusEl = document.getElementById('proxy-status');
        const proxyStatusTextEl = document.getElementById('proxy-status-text');
        const proxyPortEl = document.getElementById('proxy-port');

        proxyStatusEl.className = this.serverStatus.running ? 'status-indicator status-running' : 'status-indicator status-stopped';
        proxyStatusTextEl.textContent = this.serverStatus.running ? 'Running' : 'Stopped';
        proxyPortEl.textContent = this.serverStatus.corsPort;

        // Update URLs
        document.getElementById('direct-url').textContent = `http://localhost:${this.serverStatus.port}`;
        document.getElementById('proxy-url').textContent = `http://localhost:${this.serverStatus.corsPort}`;
        document.getElementById('health-url').textContent = `http://localhost:${this.serverStatus.port}/health`;
        document.getElementById('capabilities-url').textContent = `http://localhost:${this.serverStatus.port}/capabilities`;
        document.getElementById('integration-url').value = `http://localhost:${this.serverStatus.port}`;
        document.getElementById('proxy-integration-url').value = `http://localhost:${this.serverStatus.corsPort}`;
    }

    async restartServer() {
        try {
            this.showToast('Restarting server...', 'info');
            await ipcRenderer.invoke('restart-server');
            this.showToast('Server restarted successfully', 'success');
            setTimeout(() => this.refreshDashboard(), 2000);
        } catch (error) {
            this.showToast('Failed to restart server', 'error');
        }
    }

    async openBrowser() {
        await ipcRenderer.invoke('open-browser');
    }

    async testProxy() {
        try {
            const response = await fetch(`http://localhost:${this.serverStatus.corsPort}/health`);
            if (response.ok) {
                this.showToast('CORS proxy is working', 'success');
            } else {
                this.showToast('CORS proxy responded with error', 'warning');
            }
        } catch (error) {
            this.showToast('CORS proxy is not responding', 'error');
        }
    }

    async testConnection() {
        try {
            const response = await fetch(`http://localhost:${this.serverStatus.port}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.showToast('Server connection successful', 'success');
            } else {
                this.showToast('Server responded but not healthy', 'warning');
            }
        } catch (error) {
            this.showToast('Failed to connect to server', 'error');
        }
    }

    async openLogsFolder() {
        await ipcRenderer.invoke('open-logs-folder');
    }

    async copyUrls() {
        const urls = [
            `Direct URL: http://localhost:${this.serverStatus.port}`,
            `CORS Proxy: http://localhost:${this.serverStatus.corsPort}`,
            `Health Check: http://localhost:${this.serverStatus.port}/health`,
            `Capabilities: http://localhost:${this.serverStatus.port}/capabilities`
        ].join('\\n');

        await navigator.clipboard.writeText(urls);
        this.showToast('URLs copied to clipboard', 'success');
    }

    updateToolParameters() {
        const selectedTool = document.getElementById('tool-select').value;
        const paramsContainer = document.getElementById('tool-params');
        
        const parameters = this.toolParameters[selectedTool] || [];
        
        paramsContainer.innerHTML = '';
        
        parameters.forEach(param => {
            const paramDiv = document.createElement('div');
            paramDiv.className = 'param-input';
            
            const label = document.createElement('label');
            label.textContent = `${param.name}${param.required ? '*' : ''}: ${param.description}`;
            
            let input;
            if (param.type === 'textarea') {
                input = document.createElement('textarea');
            } else if (param.type === 'select') {
                input = document.createElement('select');
                param.options.forEach(option => {
                    const optionEl = document.createElement('option');
                    optionEl.value = option;
                    optionEl.textContent = option || '(none)';
                    input.appendChild(optionEl);
                });
            } else {
                input = document.createElement('input');
                input.type = param.type;
            }
            
            input.id = `param-${param.name}`;
            input.placeholder = param.default || '';
            
            paramDiv.appendChild(label);
            paramDiv.appendChild(input);
            paramsContainer.appendChild(paramDiv);
        });
    }

    async executeTool() {
        const selectedTool = document.getElementById('tool-select').value;
        const parameters = {};
        
        // Collect parameters
        this.toolParameters[selectedTool].forEach(param => {
            const input = document.getElementById(`param-${param.name}`);
            let value = input.value;
            
            if (value || param.required) {
                if (param.type === 'number') {
                    value = parseInt(value) || param.default;
                } else if (param.name === 'params' && value) {
                    try {
                        value = JSON.parse(value);
                    } catch (e) {
                        this.showToast('Invalid JSON in params field', 'error');
                        return;
                    }
                }
                
                if (value !== undefined && value !== '') {
                    parameters[param.name] = value;
                }
            }
        });

        try {
            const response = await fetch(`http://localhost:${this.serverStatus.port}/mcp/call`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tool: selectedTool,
                    parameters: parameters
                })
            });

            const result = await response.json();
            document.getElementById('tool-output').textContent = JSON.stringify(result, null, 2);
            
            if (response.ok) {
                this.showToast('Tool executed successfully', 'success');
            } else {
                this.showToast('Tool execution failed', 'error');
            }
        } catch (error) {
            document.getElementById('tool-output').textContent = `Error: ${error.message}`;
            this.showToast('Failed to execute tool', 'error');
        }
    }

    async refreshLogs() {
        try {
            const logs = await ipcRenderer.invoke('get-logs');
            document.getElementById('logs-content').textContent = logs;
        } catch (error) {
            this.showToast('Failed to load logs', 'error');
        }
    }

    clearLogs() {
        document.getElementById('logs-content').textContent = '';
    }

    async exportLogs() {
        try {
            const logs = await ipcRenderer.invoke('get-logs');
            const blob = new Blob([logs], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `mcp-logs-${new Date().toISOString().slice(0, 10)}.txt`;
            a.click();
            
            URL.revokeObjectURL(url);
            this.showToast('Logs exported', 'success');
        } catch (error) {
            this.showToast('Failed to export logs', 'error');
        }
    }

    async loadSettings() {
        try {
            const config = await ipcRenderer.invoke('get-config');
            
            document.getElementById('mcp-port-input').value = config.mcpPort;
            document.getElementById('cors-port-input').value = config.corsPort;
            document.getElementById('auto-start-checkbox').checked = config.autoStart;
            document.getElementById('minimize-tray-checkbox').checked = config.minimizeToTray;
            document.getElementById('notifications-checkbox').checked = config.notifications;
        } catch (error) {
            this.showToast('Failed to load settings', 'error');
        }
    }

    async saveSettings() {
        try {
            const newConfig = {
                mcpPort: parseInt(document.getElementById('mcp-port-input').value),
                corsPort: parseInt(document.getElementById('cors-port-input').value),
                autoStart: document.getElementById('auto-start-checkbox').checked,
                minimizeToTray: document.getElementById('minimize-tray-checkbox').checked,
                notifications: document.getElementById('notifications-checkbox').checked
            };

            await ipcRenderer.invoke('update-config', newConfig);
            this.showToast('Settings saved successfully', 'success');
        } catch (error) {
            this.showToast('Failed to save settings', 'error');
        }
    }

    async resetSettings() {
        document.getElementById('mcp-port-input').value = 8000;
        document.getElementById('cors-port-input').value = 8001;
        document.getElementById('auto-start-checkbox').checked = true;
        document.getElementById('minimize-tray-checkbox').checked = true;
        document.getElementById('notifications-checkbox').checked = true;
        
        await this.saveSettings();
    }

    async verifyServer() {
        try {
            const response = await fetch(`http://localhost:${this.serverStatus.port}/capabilities`);
            const data = await response.json();
            
            this.showToast(`Server verified! Found ${data.tools.length} tools`, 'success');
        } catch (error) {
            this.showToast('Server verification failed', 'error');
        }
    }

    async testTools() {
        try {
            // Test a simple get operation
            const response = await fetch(`http://localhost:${this.serverStatus.port}/mcp/call`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tool: 'sqlite_set',
                    parameters: { key: 'test_desktop', value: 'Desktop app test' }
                })
            });

            if (response.ok) {
                this.showToast('MCP tools are working correctly', 'success');
            } else {
                this.showToast('MCP tools test failed', 'error');
            }
        } catch (error) {
            this.showToast('Failed to test MCP tools', 'error');
        }
    }

    openClaude() {
        window.open('https://claude.ai', '_blank');
    }

    async copyToClipboard(button) {
        let text;
        
        if (button.dataset.copy) {
            text = button.dataset.copy;
        } else if (button.dataset.copyId) {
            const element = document.getElementById(button.dataset.copyId);
            text = element.value || element.textContent;
        }

        if (text) {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard', 'success');
        }
    }

    startAutoRefresh() {
        // Refresh dashboard every 30 seconds
        this.refreshInterval = setInterval(() => {
            if (this.currentTab === 'dashboard') {
                this.refreshDashboard();
            }
        }, 30000);
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.getElementById('toast-container').appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new MCPDesktopUI();
    app.initialize();
});
