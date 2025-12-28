/**
 * Gmail-Style Inbox JavaScript
 * ============================================================================
 * Handles message selection, bulk actions, message preview, and autosave
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================

let selectedMessages = new Set();
let currentMessageId = null;
let autosaveTimer = null;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeFeatherIcons();
});

function initializeEventListeners() {
    // Select All Checkbox
    const selectAllCheckbox = document.getElementById('selectAllMessages');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }

    // Individual Message Checkboxes
    document.querySelectorAll('.message-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleMessageSelect);
    });

    // Bulk Actions
    document.querySelectorAll('[data-action]').forEach(button => {
        button.addEventListener('click', handleBulkAction);
    });

    // Refresh Button
    const refreshButton = document.getElementById('refreshButton');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshEmails);
    }

    // Search Input
    const searchInput = document.getElementById('mailSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }

    // Keyboard Shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function initializeFeatherIcons() {
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// ============================================================================
// MESSAGE SELECTION
// ============================================================================

function handleSelectAll(event) {
    const isChecked = event.target.checked;
    const checkboxes = document.querySelectorAll('.message-checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
        const messageId = checkbox.value;

        if (isChecked) {
            selectedMessages.add(messageId);
        } else {
            selectedMessages.delete(messageId);
        }
    });

    updateBulkActionsToolbar();
}

function handleMessageSelect(event) {
    const messageId = event.target.value;

    if (event.target.checked) {
        selectedMessages.add(messageId);
    } else {
        selectedMessages.delete(messageId);
    }

    updateSelectAllCheckbox();
    updateBulkActionsToolbar();
}

function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAllMessages');
    const totalCheckboxes = document.querySelectorAll('.message-checkbox').length;

    if (totalCheckboxes === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
        return;
    }

    if (selectedMessages.size === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (selectedMessages.size === totalCheckboxes) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

function updateBulkActionsToolbar() {
    const bulkActionsButton = document.getElementById('bulkActionsDropdown');

    if (bulkActionsButton) {
        bulkActionsButton.disabled = selectedMessages.size === 0;

        // Update selection count
        let countText = bulkActionsButton.querySelector('.selection-count');
        if (selectedMessages.size > 0) {
            if (!countText) {
                countText = document.createElement('span');
                countText.className = 'selection-count';
                bulkActionsButton.appendChild(countText);
            }
            countText.textContent = ` (${selectedMessages.size})`;
        } else if (countText) {
            countText.remove();
        }
    }
}

function clearSelection() {
    selectedMessages.clear();
    document.querySelectorAll('.message-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelectAllCheckbox();
    updateBulkActionsToolbar();
}

// ============================================================================
// BULK ACTIONS
// ============================================================================

function handleBulkAction(event) {
    event.preventDefault();

    const action = event.currentTarget.getAttribute('data-action');
    const messageIds = Array.from(selectedMessages);

    if (messageIds.length === 0) {
        return;
    }

    // Show loading state
    showLoadingState();

    // Send bulk action request
    fetch('/mail/api/bulk-action/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: action,
            message_ids: messageIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message || 'Azione completata');

            // Update UI based on action
            handleBulkActionSuccess(action, messageIds);

            // Clear selection
            clearSelection();
        } else {
            showErrorMessage(data.message || 'Errore durante l\'azione');
        }
    })
    .catch(error => {
        console.error('Bulk action error:', error);
        showErrorMessage('Errore di connessione');
    })
    .finally(() => {
        hideLoadingState();
    });
}

function handleBulkActionSuccess(action, messageIds) {
    switch(action) {
        case 'delete':
            // Remove messages from list
            messageIds.forEach(id => {
                const messageElement = document.querySelector(`[data-message-id="${id}"]`);
                if (messageElement) {
                    messageElement.remove();
                }
            });
            break;

        case 'mark_read':
            messageIds.forEach(id => {
                const messageElement = document.querySelector(`[data-message-id="${id}"]`);
                if (messageElement) {
                    messageElement.classList.remove('unread');
                }
            });
            break;

        case 'mark_unread':
            messageIds.forEach(id => {
                const messageElement = document.querySelector(`[data-message-id="${id}"]`);
                if (messageElement) {
                    messageElement.classList.add('unread');
                }
            });
            break;

        case 'star':
        case 'unstar':
            // Reload to update star state
            setTimeout(() => window.location.reload(), 500);
            break;

        default:
            // For other actions, reload the page
            setTimeout(() => window.location.reload(), 500);
    }
}

// ============================================================================
// MESSAGE PREVIEW
// ============================================================================

function selectMessage(messageId) {
    // Update URL and navigate
    const url = new URL(window.location);
    url.searchParams.set('message', messageId);
    window.location.href = url.toString();
}

function toggleStar(messageId) {
    fetch(`/mail/messages/${messageId}/toggle-star/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update star icon
            const starIcons = document.querySelectorAll(`[onclick*="${messageId}"] i`);
            starIcons.forEach(icon => {
                if (data.is_starred) {
                    icon.classList.add('starred');
                } else {
                    icon.classList.remove('starred');
                }
            });

            // Re-initialize feather icons
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        }
    })
    .catch(error => {
        console.error('Toggle star error:', error);
    });
}

function replyToMessage(messageId) {
    window.location.href = `/mail/compose/?reply_to=${messageId}`;
}

function forwardMessage(messageId) {
    window.location.href = `/mail/compose/?forward=${messageId}`;
}

function deleteMessage(messageId) {
    if (!confirm('Sei sicuro di voler eliminare questo messaggio?')) {
        return;
    }

    handleBulkAction({
        preventDefault: () => {},
        currentTarget: {
            getAttribute: () => 'delete'
        }
    });
}

function markAsUnread(messageId) {
    selectedMessages.clear();
    selectedMessages.add(messageId);

    handleBulkAction({
        preventDefault: () => {},
        currentTarget: {
            getAttribute: () => 'mark_unread'
        }
    });
}

function moveToSpam(messageId) {
    selectedMessages.clear();
    selectedMessages.add(messageId);

    handleBulkAction({
        preventDefault: () => {},
        currentTarget: {
            getAttribute: () => 'move_spam'
        }
    });
}

// ============================================================================
// LABEL MANAGEMENT
// ============================================================================

function saveLabels() {
    const selectedLabels = [];
    document.querySelectorAll('.label-checkbox:checked').forEach(checkbox => {
        selectedLabels.push(checkbox.value);
    });

    if (selectedMessages.size === 0) {
        showErrorMessage('Nessun messaggio selezionato');
        return;
    }

    fetch('/mail/api/bulk-action/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: 'add_labels',
            message_ids: Array.from(selectedMessages),
            labels: selectedLabels
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Etichette aggiornate');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('labelModal'));
            if (modal) {
                modal.hide();
            }

            // Reload page to show updated labels
            setTimeout(() => window.location.reload(), 500);
        } else {
            showErrorMessage(data.message || 'Errore durante l\'aggiornamento');
        }
    })
    .catch(error => {
        console.error('Save labels error:', error);
        showErrorMessage('Errore di connessione');
    });
}

// ============================================================================
// EMAIL REFRESH
// ============================================================================

function refreshEmails() {
    const refreshButton = document.getElementById('refreshButton');
    const icon = refreshButton.querySelector('i');

    // Add spinning animation
    icon.style.animation = 'spin 1s linear infinite';
    refreshButton.disabled = true;

    fetch('/mail/api/fetch-emails/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`${data.count || 0} nuovi messaggi ricevuti`);

            // Reload page to show new messages
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showErrorMessage(data.message || 'Errore durante l\'aggiornamento');
        }
    })
    .catch(error => {
        console.error('Refresh error:', error);
        showErrorMessage('Errore di connessione');
    })
    .finally(() => {
        icon.style.animation = '';
        refreshButton.disabled = false;
    });
}

// ============================================================================
// SEARCH
// ============================================================================

function handleSearch(event) {
    const query = event.target.value.trim();

    const url = new URL(window.location);
    if (query) {
        url.searchParams.set('search', query);
    } else {
        url.searchParams.delete('search');
    }

    window.location.href = url.toString();
}

// ============================================================================
// KEYBOARD SHORTCUTS
// ============================================================================

function handleKeyboardShortcuts(event) {
    // Don't trigger shortcuts when typing in inputs
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    switch(event.key) {
        case 'c':
            // Compose new message
            window.location.href = '/mail/compose/';
            break;

        case 'r':
            // Refresh
            if (event.shiftKey) {
                event.preventDefault();
                refreshEmails();
            }
            break;

        case '/':
            // Focus search
            event.preventDefault();
            document.getElementById('mailSearchInput')?.focus();
            break;

        case 'Escape':
            // Clear selection
            clearSelection();
            break;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           document.querySelector('meta[name="csrf-token"]')?.content || '';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showSuccessMessage(message) {
    showToast(message, 'success');
}

function showErrorMessage(message) {
    showToast(message, 'error');
}

function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i data-feather="${type === 'success' ? 'check-circle' : 'alert-circle'}" class="me-2"></i>
            <span>${message}</span>
        </div>
    `;

    // Add to body
    document.body.appendChild(toast);

    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Show toast
    setTimeout(() => toast.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showLoadingState() {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Caricamento...</span>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoadingState() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// ============================================================================
// CSS for Toast Notifications (injected dynamically)
// ============================================================================

const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast-notification {
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: white;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
        max-width: 400px;
    }

    .toast-notification.show {
        opacity: 1;
        transform: translateY(0);
    }

    .toast-success {
        border-left: 4px solid #34a853;
    }

    .toast-error {
        border-left: 4px solid #ea4335;
    }

    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9998;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(toastStyles);

// ============================================================================
// AUTO-SAVE FOR DRAFTS (if on compose page)
// ============================================================================

function initializeAutosave() {
    const composeForm = document.getElementById('composeForm');
    if (!composeForm) return;

    const fields = ['to', 'subject', 'body'];
    fields.forEach(field => {
        const input = composeForm.querySelector(`[name="${field}"]`);
        if (input) {
            input.addEventListener('input', () => {
                clearTimeout(autosaveTimer);
                autosaveTimer = setTimeout(saveDraft, 2000);
            });
        }
    });
}

function saveDraft() {
    const composeForm = document.getElementById('composeForm');
    if (!composeForm) return;

    const formData = new FormData(composeForm);
    const data = Object.fromEntries(formData);

    fetch('/mail/api/save-draft/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show saved indicator
            const indicator = document.getElementById('autosaveIndicator');
            if (indicator) {
                indicator.textContent = 'Salvata';
                indicator.className = 'text-success small';
            }
        }
    })
    .catch(error => {
        console.error('Autosave error:', error);
    });
}

// Initialize autosave if on compose page
initializeAutosave();
