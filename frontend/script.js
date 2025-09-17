/**
 * ResumeRAG Frontend JavaScript
 * Handles file upload, form field extraction, and UI interactions for auto-fill demo
 */

class ResumeRAG {
    constructor() {
        this.currentSessionId = null;
        this.apiBaseUrl = '';
        this.isExtracting = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkSystemHealth();
    }

    setupEventListeners() {
        // File upload listeners
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadZone.addEventListener('drop', this.handleDrop.bind(this));
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));

        // Form field extraction listeners
        const extractButtons = document.querySelectorAll('.extract-btn');
        extractButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const fieldLabel = e.target.closest('.form-field').querySelector('input, textarea').dataset.field;
                this.extractSingleField(fieldLabel);
            });
        });

        // Form action listeners
        document.getElementById('fillAllBtn').addEventListener('click', this.fillAllFields.bind(this));
        document.getElementById('clearAllBtn').addEventListener('click', this.clearAllFields.bind(this));

        // Example field listeners
        const exampleButtons = document.querySelectorAll('.example-btn');
        exampleButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const fieldLabel = btn.getAttribute('data-field');
                this.extractSingleField(fieldLabel);
            });
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadZone').classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadZone').classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadZone').classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.uploadFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.uploadFile(files[0]);
        }
    }

    async uploadFile(file) {
        // Validate file
        const allowedTypes = ['pdf', 'docx', 'txt'];
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExtension)) {
            this.showError('uploadError', `File type not supported. Please upload PDF, DOCX, or TXT files.`);
            return;
        }

        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            this.showError('uploadError', 'File too large. Maximum size is 10MB.');
            return;
        }

        this.hideError('uploadError');
        this.showUploadProgress();

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBaseUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const result = await response.json();
            this.handleUploadSuccess(result, file);

        } catch (error) {
            this.hideUploadProgress();
            this.showError('uploadError', `Upload failed: ${error.message}`);
        }
    }

    showUploadProgress() {
        document.getElementById('uploadZone').style.display = 'none';
        document.getElementById('uploadProgress').style.display = 'block';
        
        // Simulate progress
        let progress = 0;
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            
            progressFill.style.width = progress + '%';
            progressText.textContent = `Processing... ${Math.round(progress)}%`;
        }, 200);
        
        // Store interval to clear it later
        this.progressInterval = interval;
    }

    hideUploadProgress() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        document.getElementById('uploadProgress').style.display = 'none';
        document.getElementById('uploadZone').style.display = 'block';
    }

    handleUploadSuccess(result, file) {
        this.hideUploadProgress();
        this.currentSessionId = result.session_id;

        // Show file info
        document.getElementById('fileName').textContent = result.filename;
        document.getElementById('fileSize').textContent = this.formatFileSize(result.file_size);
        document.getElementById('fileType').textContent = result.file_type.toUpperCase();
        document.getElementById('sessionId').textContent = result.session_id;
        document.getElementById('chunksCreated').textContent = result.chunks_created;
        
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('fileInfo').classList.add('fade-in');

        // Enable form demo
        this.enableFormDemo();
    }

    enableFormDemo() {
        const fillAllBtn = document.getElementById('fillAllBtn');
        const extractBtns = document.querySelectorAll('.extract-btn');
        
        fillAllBtn.disabled = false;
        extractBtns.forEach(btn => {
            btn.disabled = false;
        });
        
        // Enable example buttons
        const exampleButtons = document.querySelectorAll('.example-btn');
        exampleButtons.forEach(btn => {
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        });
    }

    async extractSingleField(fieldLabel) {
        if (!this.currentSessionId) {
            this.showError('queryError', 'Please upload a resume first.');
            return;
        }

        if (this.isExtracting) {
            return; // Prevent multiple simultaneous extractions
        }

        this.isExtracting = true;
        const inputElement = this.getInputByFieldLabel(fieldLabel);
        const extractBtn = inputElement?.parentElement.querySelector('.extract-btn');
        
        if (extractBtn) {
            this.setButtonLoading(extractBtn, true);
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/extract`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    field_label: fieldLabel,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Extraction failed');
            }

            const result = await response.json();
            this.displayFieldResult(result, inputElement);
            this.logExtraction(result);

        } catch (error) {
            this.showError('queryError', `Failed to extract ${fieldLabel}: ${error.message}`);
            if (inputElement) {
                inputElement.classList.add('error');
            }
            this.logExtraction({ field_label: fieldLabel, value: null, confidence: 0, error: error.message });
        } finally {
            this.isExtracting = false;
            if (extractBtn) {
                this.setButtonLoading(extractBtn, false);
            }
        }
    }

    async fillAllFields() {
        if (!this.currentSessionId) {
            this.showError('queryError', 'Please upload a resume first.');
            return;
        }

        const fillAllBtn = document.getElementById('fillAllBtn');
        const fillAllText = document.getElementById('fillAllText');
        const fillAllSpinner = document.getElementById('fillAllSpinner');

        // Get all form fields
        const allFields = this.getAllFormFields();
        if (allFields.length === 0) {
            this.showError('queryError', 'No form fields found.');
            return;
        }

        fillAllBtn.disabled = true;
        fillAllText.textContent = 'Extracting...';
        fillAllSpinner.style.display = 'block';
        
        this.clearExtractionLog();
        this.showExtractionLog();

        try {
            const response = await fetch(`${this.apiBaseUrl}/extract/bulk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fields: allFields,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Bulk extraction failed');
            }

            const result = await response.json();
            this.displayBulkResults(result);
            
            // Show summary
            const successCount = result.extracted_fields;
            const totalCount = result.total_fields;
            this.logExtraction({
                field_label: 'SUMMARY',
                value: `Filled ${successCount}/${totalCount} fields in ${Math.round(result.processing_time_ms)}ms`,
                confidence: successCount / totalCount,
                success: true
            });

        } catch (error) {
            this.showError('queryError', `Bulk extraction failed: ${error.message}`);
            this.logExtraction({ field_label: 'ERROR', value: null, confidence: 0, error: error.message });
        } finally {
            fillAllBtn.disabled = false;
            fillAllText.textContent = '🎯 Auto-Fill All Fields';
            fillAllSpinner.style.display = 'none';
        }
    }

    displayFieldResult(result, inputElement) {
        if (inputElement && result.value) {
            inputElement.value = result.value;
            inputElement.classList.remove('error');
            inputElement.classList.add('filled');
            
            // Add confidence indicator
            const confidence = Math.round(result.confidence * 100);
            inputElement.title = `Confidence: ${confidence}% (${result.field_type})`;
        }
    }

    displayBulkResults(bulkResult) {
        bulkResult.fields.forEach(fieldResult => {
            const inputElement = this.getInputByFieldLabel(fieldResult.field_label);
            this.displayFieldResult(fieldResult, inputElement);
            this.logExtraction(fieldResult);
        });
    }

    getInputByFieldLabel(fieldLabel) {
        const inputs = document.querySelectorAll('input[data-field], textarea[data-field]');
        for (const input of inputs) {
            if (input.dataset.field === fieldLabel) {
                return input;
            }
        }
        return null;
    }

    getAllFormFields() {
        const inputs = document.querySelectorAll('input[data-field], textarea[data-field]');
        return Array.from(inputs).map(input => input.dataset.field);
    }

    clearAllFields() {
        const inputs = document.querySelectorAll('input[data-field], textarea[data-field]');
        inputs.forEach(input => {
            input.value = '';
            input.classList.remove('filled', 'error');
            input.title = '';
        });
        this.hideExtractionLog();
        this.hideError('queryError');
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.innerHTML = '⏳';
            button.disabled = true;
        } else {
            button.innerHTML = '🔍';
            button.disabled = false;
        }
    }

    logExtraction(result) {
        const logContent = document.getElementById('logContent');
        if (!logContent) return;

        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        if (result.success) {
            entry.classList.add('success');
        } else if (result.error) {
            entry.classList.add('error');
        } else if (result.confidence < 0.5) {
            entry.classList.add('warning');
        } else {
            entry.classList.add('success');
        }

        const timestamp = new Date().toLocaleTimeString();
        const confidenceStr = result.confidence ? `(${Math.round(result.confidence * 100)}%)` : '';
        const valueStr = result.value || result.error || 'No value found';
        
        entry.innerHTML = `
            <strong>[${timestamp}] ${result.field_label}</strong><br>
            ${valueStr} ${confidenceStr}
        `;
        
        logContent.appendChild(entry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    showExtractionLog() {
        document.getElementById('extractionLog').style.display = 'block';
    }

    hideExtractionLog() {
        document.getElementById('extractionLog').style.display = 'none';
    }

    clearExtractionLog() {
        const logContent = document.getElementById('logContent');
        if (logContent) {
            logContent.innerHTML = '';
        }
    }

    async checkSystemHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const health = await response.json();
            
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('statusText');
            
            statusDot.className = 'status-dot';
            
            if (health.status === 'healthy') {
                statusDot.classList.add('healthy');
                statusText.textContent = 'System ready for form filling';
            } else if (health.status === 'degraded') {
                statusDot.classList.add('degraded');
                statusText.textContent = 'System partially available';
            } else {
                statusDot.classList.add('unhealthy');
                statusText.textContent = 'System unavailable';
            }
            
        } catch (error) {
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('statusText');
            
            statusDot.className = 'status-dot unhealthy';
            statusText.textContent = 'Cannot connect to server';
        }
    }

    showError(elementId, message) {
        const errorEl = document.getElementById(elementId);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }

    hideError(elementId) {
        const errorEl = document.getElementById(elementId);
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new ResumeRAG();
});