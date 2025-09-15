// CapiStack JavaScript Application

// Global app object
window.CapiStack = {
    // Configuration
    config: {
        apiBase: '/api',
        refreshInterval: 5000 // 5 seconds
    },
    
    // Utility functions
    utils: {
        // Format timestamp
        formatTimestamp: function(timestamp) {
            return new Date(timestamp).toLocaleString();
        },
        
        // Format duration
        formatDuration: function(seconds) {
            if (seconds < 60) {
                return seconds + 's';
            } else if (seconds < 3600) {
                return Math.floor(seconds / 60) + 'm ' + (seconds % 60) + 's';
            } else {
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                return hours + 'h ' + minutes + 'm';
            }
        },
        
        // Show notification
        showNotification: function(message, type = 'info') {
            const alertClass = {
                'success': 'alert-success',
                'error': 'alert-danger',
                'warning': 'alert-warning',
                'info': 'alert-info'
            }[type] || 'alert-info';
            
            const alertHtml = `
                <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            // Insert at the top of main content
            const main = document.querySelector('main .container');
            if (main) {
                main.insertAdjacentHTML('afterbegin', alertHtml);
            }
        },
        
        // Make API request
        apiRequest: function(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                }
            };
            
            const finalOptions = { ...defaultOptions, ...options };
            
            return fetch(url, finalOptions)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                });
        }
    },
    
    // Deployment management
    deployments: {
        // Get deployment status
        getStatus: function(deploymentId) {
            return CapiStack.utils.apiRequest(`/api/deployments/${deploymentId}/status`);
        },
        
        // Cancel deployment
        cancel: function(deploymentId) {
            return CapiStack.utils.apiRequest(`/api/deployments/${deploymentId}/cancel`, {
                method: 'POST'
            });
        },
        
        // Refresh deployment data
        refresh: function(deploymentId) {
            return CapiStack.utils.apiRequest(`/api/deployments/${deploymentId}`);
        }
    },
    
    // Git references
    refs: {
        // Get branches
        getBranches: function() {
            return CapiStack.utils.apiRequest('/api/refs/branches');
        },
        
        // Get tags
        getTags: function() {
            return CapiStack.utils.apiRequest('/api/refs/tags');
        },
        
        // Get releases
        getReleases: function() {
            return CapiStack.utils.apiRequest('/api/refs/releases');
        }
    },
    
    // Real-time updates
    realtime: {
        // Event source connections
        connections: new Map(),
        
        // Connect to deployment logs
        connectLogs: function(deploymentId, callback) {
            const url = `/deployments/${deploymentId}/stream`;
            const eventSource = new EventSource(url);
            
            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    callback(data);
                } catch (e) {
                    console.error('Error parsing log data:', e);
                }
            };
            
            eventSource.onerror = function(event) {
                console.error('SSE connection error:', event);
                callback({ error: 'Connection lost' });
            };
            
            this.connections.set(deploymentId, eventSource);
            return eventSource;
        },
        
        // Disconnect from deployment logs
        disconnectLogs: function(deploymentId) {
            const eventSource = this.connections.get(deploymentId);
            if (eventSource) {
                eventSource.close();
                this.connections.delete(deploymentId);
            }
        },
        
        // Disconnect all connections
        disconnectAll: function() {
            this.connections.forEach((eventSource, deploymentId) => {
                eventSource.close();
            });
            this.connections.clear();
        }
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up global error handling
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        CapiStack.utils.showNotification('An unexpected error occurred', 'error');
    });
    
    // Set up unhandled promise rejection handling
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        CapiStack.utils.showNotification('An unexpected error occurred', 'error');
    });
    
    // Clean up connections on page unload
    window.addEventListener('beforeunload', function() {
        CapiStack.realtime.disconnectAll();
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CapiStack;
}
