// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// State
let allTools = [];

// DOM Elements
const healthIndicator = document.getElementById('health-indicator');
const healthText = document.getElementById('health-text');
const agentStatus = document.getElementById('agent-status');
const llmStatus = document.getElementById('llm-status');
const toolsCount = document.getElementById('tools-count');
const memoryCount = document.getElementById('memory-count');
const taskForm = document.getElementById('task-form');
const taskResult = document.getElementById('task-result');
const resultTaskId = document.getElementById('result-task-id');
const resultStatus = document.getElementById('result-status');
const resultConfidence = document.getElementById('result-confidence');
const resultExecutionTime = document.getElementById('result-execution-time');
const resultToolsUsed = document.getElementById('result-tools-used');
const resultOutput = document.getElementById('result-output');
const toolsContainer = document.getElementById('tools-container');
const memoriesContainer = document.getElementById('memories-container');
const auditContainer = document.getElementById('audit-container');
const toolSelect = document.getElementById('tool-select');
const toolParamsContainer = document.getElementById('tool-params-container');
const executeToolBtn = document.getElementById('execute-tool-btn');
const toolResult = document.getElementById('tool-result');
const toolResultOutput = document.getElementById('tool-result-output');
const clearMemoriesBtn = document.getElementById('clear-memories-btn');

// Fetch health status
async function fetchHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        // Update system status indicator
        if (data.status === 'healthy') {
            healthIndicator.className = 'status-indicator healthy';
            healthText.textContent = 'System Healthy';
        } else if (data.status === 'degraded') {
            healthIndicator.className = 'status-indicator degraded';
            healthText.textContent = 'System Degraded';
        } else {
            healthIndicator.className = 'status-indicator unhealthy';
            healthText.textContent = 'System Unhealthy';
        }
        
        // Update health details
        agentStatus.textContent = data.agent?.state || 'Unknown';
        llmStatus.textContent = data.llm_available ? 'Connected' : 'Disconnected';
        toolsCount.textContent = data.tools_count || 0;
        memoryCount.textContent = data.memory_stats?.total_memories || 0;
        
    } catch (error) {
        console.error('Failed to fetch health:', error);
        healthIndicator.className = 'status-indicator unhealthy';
        healthText.textContent = 'Connection Failed';
        agentStatus.textContent = 'Unknown';
        llmStatus.textContent = 'Unknown';
    }
}

// Execute task
async function executeTask(taskData) {
    try {
        const submitButton = taskForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Executing...';
        
        const response = await fetch(`${API_BASE_URL}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(taskData),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Display results
        resultTaskId.textContent = result.task_id;
        resultStatus.textContent = result.state;
        resultStatus.className = result.state === 'completed' ? 'status-allowed' : 'status-blocked';
        resultConfidence.textContent = `${(result.confidence * 100).toFixed(1)}%`;
        resultExecutionTime.textContent = result.execution_time.toFixed(2);
        resultToolsUsed.textContent = result.tools_used.join(', ') || 'None';
        
        if (result.result) {
            resultOutput.textContent = JSON.stringify(result.result, null, 2);
        } else {
            resultOutput.textContent = 'No output';
        }
        
        taskResult.classList.remove('hidden');
        
        // Refresh health after task execution
        await fetchHealth();
        
    } catch (error) {
        console.error('Failed to execute task:', error);
        alert(`Task execution failed: ${error.message}`);
    } finally {
        const submitButton = taskForm.querySelector('button[type="submit"]');
        submitButton.disabled = false;
        submitButton.textContent = 'Execute Task';
    }
}

// Fetch tools
async function fetchTools() {
    try {
        const response = await fetch(`${API_BASE_URL}/tools`);
        allTools = await response.json();
        
        if (allTools.length === 0) {
            toolsContainer.innerHTML = '<p class="loading">No tools available</p>';
            return;
        }
        
        // Populate tool select dropdown
        if (toolSelect) {
            toolSelect.innerHTML = '<option value="">-- Choose a tool --</option>' + 
                allTools.map(tool => `<option value="${tool.name}">${tool.name}</option>`).join('');
        }
        
        // Update tools browser grid
        toolsContainer.innerHTML = allTools.map(tool => `
            <div class="tool-item" onclick="selectTool('${tool.name}')">
                <h4>${tool.name}</h4>
                <p>${tool.description}</p>
                <div class="tool-meta">
                    <span class="tool-tag">${tool.category}</span>
                    ${tool.read_only ? '<span class="tool-tag read-only">Read Only</span>' : ''}
                    ${tool.requires_approval ? '<span class="tool-tag requires-approval">Requires Approval</span>' : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to fetch tools:', error);
        toolsContainer.innerHTML = '<p class="loading">Failed to load tools</p>';
    }
}

// Select tool from browser grid
function selectTool(toolName) {
    if (toolSelect) {
        toolSelect.value = toolName;
        populateToolParams(toolName);
        // Scroll to tool execution section
        document.getElementById('tool-select').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Fetch memories
async function fetchMemories() {
    try {
        const response = await fetch(`${API_BASE_URL}/memory?limit=10`);
        const data = await response.json();
        const memories = data.memories || [];
        
        if (memories.length === 0) {
            memoriesContainer.innerHTML = '<p class="loading">No memories stored yet</p>';
            return;
        }
        
        memoriesContainer.innerHTML = memories.map(memory => `
            <div class="memory-item">
                <h4>${memory.content || 'Unknown'}</h4>
                <div class="memory-meta">
                    <span>Type: ${memory.memory_type || 'Unknown'}</span>
                    <span>Importance: ${(memory.importance * 100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to fetch memories:', error);
        memoriesContainer.innerHTML = '<p class="loading">Failed to load memories</p>';
    }
}

// Fetch audit log
async function fetchAuditLog() {
    try {
        const response = await fetch(`${API_BASE_URL}/audit?limit=50`);
        const data = await response.json();
        const auditLog = data.audit_log || [];
        
        if (auditLog.length === 0) {
            auditContainer.innerHTML = '<p class="loading">No audit entries yet</p>';
            return;
        }
        
        auditContainer.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Action</th>
                        <th>Result</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${auditLog.map(entry => `
                        <tr>
                            <td>${new Date(entry.timestamp || Date.now()).toLocaleString()}</td>
                            <td>${entry.action || 'Unknown'}</td>
                            <td class="${entry.allowed ? 'status-allowed' : 'status-blocked'}">
                                ${entry.allowed ? 'Allowed' : 'Blocked'}
                            </td>
                            <td>${entry.reason || 'N/A'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
    } catch (error) {
        console.error('Failed to fetch audit log:', error);
        auditContainer.innerHTML = '<p class="loading">Failed to load audit log</p>';
    }
}

// Event Listeners
taskForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const goal = document.getElementById('task-goal').value;
    const description = document.getElementById('task-description').value;
    const priority = parseInt(document.getElementById('task-priority').value);
    const contextRaw = document.getElementById('task-context').value;
    
    let context;
    try {
        context = JSON.parse(contextRaw);
    } catch (error) {
        alert('Invalid JSON in context field');
        return;
    }
    
    const taskData = {
        goal,
        description,
        priority,
        context,
    };
    
    await executeTask(taskData);
});

// Direct tool execution
function populateToolParams(toolName) {
    const tool = allTools.find(t => t.name === toolName);
    if (!tool) {
        toolParamsContainer.innerHTML = '';
        executeToolBtn.disabled = true;
        return;
    }
    
    executeToolBtn.disabled = false;
    
    const params = tool.parameters || {};
    const paramKeys = Object.keys(params);
    
    if (paramKeys.length === 0) {
        toolParamsContainer.innerHTML = '<p class="loading">No parameters required</p>';
        return;
    }
    
    toolParamsContainer.innerHTML = paramKeys.map(key => {
        const spec = params[key];
        const required = spec.required !== false;
        const defaultVal = spec.default !== null && spec.default !== undefined ? spec.default : '';
        return `
            <div class="form-group">
                <label for="param-${key}">${key} ${required ? '*' : ''} (${spec.type || 'any'})</label>
                <input type="text" id="param-${key}" data-param="${key}" value="${defaultVal}" placeholder="${spec.description || ''}">
            </div>
        `;
    }).join('');
}

async function executeDirectTool(toolName) {
    const params = {};
    toolParamsContainer.querySelectorAll('input[data-param]').forEach(input => {
        const key = input.dataset.param;
        let value = input.value;
        
        // Try to parse as JSON if it looks like JSON
        if (value.startsWith('{') || value.startsWith('[')) {
            try {
                value = JSON.parse(value);
            } catch (e) {
                // Keep as string
            }
        }
        
        // Try to parse numbers
        if (!isNaN(value) && value !== '') {
            value = Number(value);
        }
        
        // Try to parse booleans
        if (value === 'true') value = true;
        if (value === 'false') value = false;
        
        params[key] = value;
    });
    
    try {
        executeToolBtn.disabled = true;
        executeToolBtn.textContent = 'Executing...';
        
        const response = await fetch(`${API_BASE_URL}/tools/${toolName}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        
        const result = await response.json();
        
        toolResultOutput.textContent = JSON.stringify(result, null, 2);
        toolResult.classList.remove('hidden');
        
    } catch (error) {
        console.error('Failed to execute tool:', error);
        alert(`Tool execution failed: ${error.message}`);
    } finally {
        executeToolBtn.disabled = false;
        executeToolBtn.textContent = 'Execute Tool';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch
    fetchHealth();
    fetchTools();
    fetchMemories();
    fetchAuditLog();
    
    // Poll health status every 10 seconds
    setInterval(fetchHealth, 10000);
    
    // Tool selection change
    if (toolSelect) {
        toolSelect.addEventListener('change', (e) => {
            populateToolParams(e.target.value);
        });
    }
    
    // Tool execution button
    if (executeToolBtn) {
        executeToolBtn.addEventListener('click', () => {
            const toolName = toolSelect.value;
            if (toolName) {
                executeDirectTool(toolName);
            }
        });
    }
    
    // Clear memories button
    if (clearMemoriesBtn) {
        clearMemoriesBtn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to delete all memories?')) return;
            
            try {
                const response = await fetch(`${API_BASE_URL}/memory`, {
                    method: 'DELETE',
                });
                const data = await response.json();
                
                if (data.success) {
                    memoriesContainer.innerHTML = '<p class="loading">No memories stored</p>';
                    memoryCount.textContent = '0';
                }
            } catch (error) {
                console.error('Failed to clear memories:', error);
                alert('Failed to clear memories');
            }
        });
    }
});