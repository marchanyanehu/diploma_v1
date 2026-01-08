/**
 * Intelligent Web Data Aggregator - Frontend Application
 * A clean, simple frontend for presentation purposes
 */

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    POLL_INTERVAL: 2000, // ms
    TOKEN_KEY: 'auth_token',
    USERNAME_KEY: 'username'
};

// State Management
const state = {
    token: localStorage.getItem(CONFIG.TOKEN_KEY) || null,
    username: localStorage.getItem(CONFIG.USERNAME_KEY) || null,
    currentTaskId: null,
    pollTimer: null,
    tasks: [],
    scheduledJobs: []
};

// DOM Elements
const elements = {
    // Auth
    authSection: document.getElementById('auth-section'),
    dashboardSection: document.getElementById('dashboard-section'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    authError: document.getElementById('auth-error'),
    showRegister: document.getElementById('show-register'),
    showLogin: document.getElementById('show-login'),
    logoutBtn: document.getElementById('logout-btn'),
    usernameDisplay: document.getElementById('username-display'),
    
    // Tabs
    tabs: document.querySelectorAll('.tab'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    
    // Scrape
    scrapeForm: document.getElementById('scrape-form'),
    scrapeUrl: document.getElementById('scrape-url'),
    scrapePrompt: document.getElementById('scrape-prompt'),
    promptLength: document.getElementById('prompt-length'),
    latestResult: document.getElementById('latest-result'),
    resultStatus: document.getElementById('result-status'),
    resultContent: document.getElementById('result-content'),
    exampleBtns: document.querySelectorAll('.example-btn'),
    
    // Tasks
    tasksList: document.getElementById('tasks-list'),
    refreshTasks: document.getElementById('refresh-tasks'),
    
    // Schedule
    scheduleForm: document.getElementById('schedule-form'),
    schedulesList: document.getElementById('schedules-list'),
    showScheduleForm: document.getElementById('show-schedule-form'),
    cancelSchedule: document.getElementById('cancel-schedule'),
    scheduleUrl: document.getElementById('schedule-url'),
    scheduleCron: document.getElementById('schedule-cron'),
    schedulePrompt: document.getElementById('schedule-prompt'),
    cronBtns: document.querySelectorAll('.cron-btn'),
    
    // Utils
    toastContainer: document.getElementById('toast-container'),
    loadingOverlay: document.getElementById('loading-overlay')
};

// API Functions
const api = {
    async request(endpoint, options = {}) {
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (state.token) {
            headers['Authorization'] = `Bearer ${state.token}`;
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers
            });
            
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Request failed');
            }
            
            return data;
        } catch (error) {
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                throw new Error('Unable to connect to server. Please check if the API is running.');
            }
            throw error;
        }
    },
    
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        
        return data;
    },
    
    async register(username, password, email) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, password, email: email || null })
        });
    },
    
    async createTask(url, prompt) {
        return this.request('/api/v1/process', {
            method: 'POST',
            body: JSON.stringify({ url, prompt })
        });
    },
    
    async getTaskStatus(taskId) {
        return this.request(`/api/v1/status/${taskId}`);
    },
    
    async getTaskResult(taskId) {
        return this.request(`/api/v1/result/${taskId}`);
    },
    
    async getUserActivity() {
        return this.request('/api/v1/users/me/activity');
    },
    
    async createScheduledJob(url, prompt, scheduleCron) {
        return this.request('/api/v1/jobs', {
            method: 'POST',
            body: JSON.stringify({ url, prompt, schedule_cron: scheduleCron })
        });
    },
    
    async deleteScheduledJob(jobId) {
        return this.request(`/api/v1/jobs/${jobId}`, {
            method: 'DELETE'
        });
    }
};

// UI Functions
function showLoading() {
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showAuthError(message) {
    elements.authError.textContent = message;
    elements.authError.classList.remove('hidden');
}

function hideAuthError() {
    elements.authError.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function truncateUrl(url, maxLength = 50) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// Auth Functions
function login(token, username) {
    state.token = token;
    state.username = username;
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
    localStorage.setItem(CONFIG.USERNAME_KEY, username);
    
    elements.authSection.classList.add('hidden');
    elements.dashboardSection.classList.remove('hidden');
    elements.usernameDisplay.textContent = username;
    
    loadUserActivity();
}

function logout() {
    state.token = null;
    state.username = null;
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USERNAME_KEY);
    
    if (state.pollTimer) {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
    }
    
    elements.dashboardSection.classList.add('hidden');
    elements.authSection.classList.remove('hidden');
    elements.loginForm.reset();
    elements.registerForm.reset();
    hideAuthError();
}

function checkAuth() {
    if (state.token) {
        elements.authSection.classList.add('hidden');
        elements.dashboardSection.classList.remove('hidden');
        elements.usernameDisplay.textContent = state.username || 'User';
        loadUserActivity();
    }
}

// Tab Navigation
function switchTab(tabName) {
    elements.tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    
    elements.tabPanes.forEach(pane => {
        pane.classList.toggle('hidden', pane.id !== `${tabName}-tab`);
        pane.classList.toggle('active', pane.id === `${tabName}-tab`);
    });
}

// Task Functions
async function loadUserActivity() {
    try {
        const activity = await api.getUserActivity();
        state.tasks = activity.tasks || [];
        state.scheduledJobs = activity.scheduled_jobs || [];
        renderTasks();
        renderScheduledJobs();
    } catch (error) {
        console.error('Failed to load activity:', error);
        // Don't show error toast on initial load failure
    }
}

function renderTasks() {
    if (state.tasks.length === 0) {
        elements.tasksList.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"></path>
                    <rect x="9" y="3" width="6" height="4" rx="1"></rect>
                </svg>
                <p>No tasks yet. Create your first scraping task!</p>
            </div>
        `;
        return;
    }
    
    const tasksHtml = state.tasks.map(task => `
        <div class="task-item" data-task-id="${task.task_id}">
            <div class="task-info">
                <div class="task-url">${escapeHtml(truncateUrl(task.url || 'N/A', 60))}</div>
                <div class="task-prompt">${escapeHtml(task.prompt || task.message || '')}</div>
                <div class="task-meta">
                    <span>Created: ${formatDate(task.created_at)}</span>
                    <span class="status-badge status-${task.status.toLowerCase().replace('_', '-')}">${task.status}</span>
                </div>
            </div>
            <div class="task-actions">
                ${task.status === 'SUCCESS' ? `<button class="btn-view" onclick="viewTaskResult('${task.task_id}')">View Result</button>` : ''}
            </div>
        </div>
    `).join('');
    
    elements.tasksList.innerHTML = tasksHtml;
}

async function viewTaskResult(taskId) {
    showLoading();
    try {
        const result = await api.getTaskResult(taskId);
        displayResult(result);
        switchTab('scrape');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function displayResult(result) {
    elements.latestResult.classList.remove('hidden');
    
    const statusClass = `status-${result.status.toLowerCase().replace('_', '-')}`;
    elements.resultStatus.className = `status-badge ${statusClass}`;
    elements.resultStatus.textContent = result.status;
    
    let dataHtml = '';
    
    if (result.data && result.data.length > 0) {
        // Check if data is an array of objects with consistent keys
        const firstItem = result.data[0];
        if (typeof firstItem === 'object' && !Array.isArray(firstItem)) {
            const keys = Object.keys(firstItem);
            if (keys.length > 0 && keys.length <= 5) {
                // Render as table
                dataHtml = `
                    <table class="result-table">
                        <thead>
                            <tr>
                                ${keys.map(key => `<th>${escapeHtml(key)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${result.data.slice(0, 50).map(item => `
                                <tr>
                                    ${keys.map(key => `<td>${escapeHtml(String(item[key] ?? ''))}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    ${result.data.length > 50 ? `<p style="margin-top:1rem;color:var(--text-muted);font-size:0.875rem;">Showing first 50 of ${result.data.length} results</p>` : ''}
                `;
            } else {
                // Too many columns, show as JSON
                dataHtml = `<pre class="result-data">${escapeHtml(JSON.stringify(result.data, null, 2))}</pre>`;
            }
        } else {
            // Array of primitives or nested arrays
            dataHtml = `<pre class="result-data">${escapeHtml(JSON.stringify(result.data, null, 2))}</pre>`;
        }
    } else {
        dataHtml = '<p style="color:var(--text-muted);">No data extracted</p>';
    }
    
    const metaHtml = `
        <div class="result-meta">
            <span><strong>URL:</strong> ${escapeHtml(truncateUrl(result.url || 'N/A', 40))}</span>
            ${result.processing_time ? `<span><strong>Time:</strong> ${result.processing_time.toFixed(2)}s</span>` : ''}
            <span><strong>Items:</strong> ${result.data ? result.data.length : 0}</span>
        </div>
    `;
    
    elements.resultContent.innerHTML = dataHtml + metaHtml;
}

async function pollTaskStatus(taskId) {
    try {
        const status = await api.getTaskStatus(taskId);
        
        if (status.status === 'SUCCESS') {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
            
            const result = await api.getTaskResult(taskId);
            displayResult(result);
            showToast('Extraction completed successfully!', 'success');
            loadUserActivity();
        } else if (status.status === 'FAILED') {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
            
            elements.latestResult.classList.remove('hidden');
            elements.resultStatus.className = 'status-badge status-failed';
            elements.resultStatus.textContent = 'FAILED';
            elements.resultContent.innerHTML = `
                <div style="color: var(--error);">
                    <p><strong>Error:</strong> ${escapeHtml(status.message || 'Task failed')}</p>
                </div>
            `;
            showToast('Extraction failed', 'error');
            loadUserActivity();
        } else {
            // Still in progress
            elements.latestResult.classList.remove('hidden');
            elements.resultStatus.className = `status-badge status-${status.status.toLowerCase().replace('_', '-')}`;
            elements.resultStatus.textContent = status.status;
            elements.resultContent.innerHTML = `
                <div style="display:flex;align-items:center;gap:1rem;">
                    <div class="spinner"></div>
                    <p>Processing... ${status.progress ? `${status.progress}%` : ''}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Poll error:', error);
    }
}

// Scheduled Jobs Functions
function renderScheduledJobs() {
    if (state.scheduledJobs.length === 0) {
        elements.schedulesList.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <p>No scheduled jobs. Create one to automate your scraping!</p>
            </div>
        `;
        return;
    }
    
    const jobsHtml = state.scheduledJobs.map(job => `
        <div class="schedule-item" data-job-id="${job.id}">
            <div class="schedule-info">
                <div class="schedule-url">${escapeHtml(truncateUrl(job.url, 60))}</div>
                <span class="schedule-cron">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    ${escapeHtml(job.schedule_cron)}
                </span>
                <div class="schedule-prompt">${escapeHtml(job.prompt)}</div>
                <div class="schedule-meta">
                    <span>Next run: ${formatDate(job.next_run_at)}</span>
                    <span>Last run: ${formatDate(job.last_run_at)}</span>
                </div>
            </div>
            <div class="task-actions">
                <button class="btn-delete" onclick="deleteScheduledJob(${job.id})">Delete</button>
            </div>
        </div>
    `).join('');
    
    elements.schedulesList.innerHTML = jobsHtml;
}

async function deleteScheduledJob(jobId) {
    if (!confirm('Are you sure you want to delete this scheduled job?')) {
        return;
    }
    
    showLoading();
    try {
        await api.deleteScheduledJob(jobId);
        showToast('Scheduled job deleted', 'success');
        state.scheduledJobs = state.scheduledJobs.filter(j => j.id !== jobId);
        renderScheduledJobs();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Event Listeners
function setupEventListeners() {
    // Auth form switching
    elements.showRegister.addEventListener('click', (e) => {
        e.preventDefault();
        elements.loginForm.classList.add('hidden');
        elements.registerForm.classList.remove('hidden');
        hideAuthError();
    });
    
    elements.showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        elements.registerForm.classList.add('hidden');
        elements.loginForm.classList.remove('hidden');
        hideAuthError();
    });
    
    // Login form
    elements.loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideAuthError();
        showLoading();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        try {
            const data = await api.login(username, password);
            login(data.access_token, username);
            showToast('Welcome back!', 'success');
        } catch (error) {
            showAuthError(error.message);
        } finally {
            hideLoading();
        }
    });
    
    // Register form
    elements.registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideAuthError();
        showLoading();
        
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        
        try {
            await api.register(username, password, email);
            // Auto-login after registration
            const data = await api.login(username, password);
            login(data.access_token, username);
            showToast('Account created successfully!', 'success');
        } catch (error) {
            showAuthError(error.message);
        } finally {
            hideLoading();
        }
    });
    
    // Logout
    elements.logoutBtn.addEventListener('click', logout);
    
    // Tab navigation
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
    
    // Scrape form
    elements.scrapeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        showLoading();
        
        const url = elements.scrapeUrl.value;
        const prompt = elements.scrapePrompt.value;
        
        try {
            const response = await api.createTask(url, prompt);
            state.currentTaskId = response.task_id;
            
            showToast('Task created! Processing...', 'info');
            
            // Start polling
            if (state.pollTimer) {
                clearInterval(state.pollTimer);
            }
            
            // Initial status display
            elements.latestResult.classList.remove('hidden');
            elements.resultStatus.className = 'status-badge status-pending';
            elements.resultStatus.textContent = 'PENDING';
            elements.resultContent.innerHTML = `
                <div style="display:flex;align-items:center;gap:1rem;">
                    <div class="spinner"></div>
                    <p>Starting extraction...</p>
                </div>
            `;
            
            state.pollTimer = setInterval(() => pollTaskStatus(state.currentTaskId), CONFIG.POLL_INTERVAL);
            
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Prompt character count
    elements.scrapePrompt.addEventListener('input', () => {
        elements.promptLength.textContent = elements.scrapePrompt.value.length;
    });
    
    // Example prompts
    elements.exampleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.scrapePrompt.value = btn.dataset.prompt;
            elements.promptLength.textContent = btn.dataset.prompt.length;
        });
    });
    
    // Refresh tasks
    elements.refreshTasks.addEventListener('click', () => {
        loadUserActivity();
        showToast('Tasks refreshed', 'info');
    });
    
    // Schedule form toggle
    elements.showScheduleForm.addEventListener('click', () => {
        elements.scheduleForm.classList.toggle('hidden');
    });
    
    elements.cancelSchedule.addEventListener('click', () => {
        elements.scheduleForm.classList.add('hidden');
        elements.scheduleForm.reset();
    });
    
    // Schedule form submit
    elements.scheduleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        showLoading();
        
        const url = elements.scheduleUrl.value;
        const cron = elements.scheduleCron.value;
        const prompt = elements.schedulePrompt.value;
        
        try {
            const job = await api.createScheduledJob(url, prompt, cron);
            state.scheduledJobs.push(job);
            renderScheduledJobs();
            
            elements.scheduleForm.classList.add('hidden');
            elements.scheduleForm.reset();
            
            showToast('Scheduled job created!', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Cron helper buttons
    elements.cronBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.scheduleCron.value = btn.dataset.cron;
        });
    });
}

// Make functions available globally for inline handlers
window.viewTaskResult = viewTaskResult;
window.deleteScheduledJob = deleteScheduledJob;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAuth();
});
