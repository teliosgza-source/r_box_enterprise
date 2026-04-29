class TeliosGeoProcessor {
    constructor() {
        this.jobs = new Map();
        this.currentJob = null;
        this.scanData = null;
        this.selectedCountries = new Set();
        this.pollingInterval = null;
        this.processingLogs = [];
        this.displayedLogCount = 0;
        this.lastMessage = '';
        this.currentStep = '';
        this.currentCountry = '';
        this.steps = [
            'Initializing',
            'Scanning directories',
            'Reading GeoJSON files',
            'Extracting Level 0 data',
            'Extracting Level 1 data',
            'Extracting Level 2 data',
            'Transforming data',
            'Generating Telios keys',
            'Assigning Unit IDs',
            'Saving to database',
            'Creating output files',
            'Finalizing'
        ];
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.checkConnection();
        await this.loadProcessedData();
        this.startHealthCheck();
    }

    bindEvents() {
        const elements = {
            selectDataDir: document.getElementById('selectDataDir'),
            startProcessing: document.getElementById('startProcessing'),
            selectAllBtn: document.getElementById('selectAllBtn'),
            clearAllBtn: document.getElementById('clearAllBtn'),
            refreshScanBtn: document.getElementById('refreshScanBtn'),
            refreshDataBtn: document.getElementById('refreshDataBtn'),
            exportAllBtn: document.getElementById('exportAllBtn'),
            validateAllBtn: document.getElementById('validateAllBtn'),
            clearLogsBtn: document.getElementById('clearLogsBtn'),
            countrySearch: document.getElementById('countrySearch')
        };
        
        if (elements.selectDataDir) elements.selectDataDir.addEventListener('click', () => this.selectDataDir());
        if (elements.startProcessing) elements.startProcessing.addEventListener('click', () => this.startProcessing());
        if (elements.selectAllBtn) elements.selectAllBtn.addEventListener('click', () => this.selectAllCountries());
        if (elements.clearAllBtn) elements.clearAllBtn.addEventListener('click', () => this.clearAllCountries());
        if (elements.refreshScanBtn) elements.refreshScanBtn.addEventListener('click', () => this.refreshScan());
        if (elements.refreshDataBtn) elements.refreshDataBtn.addEventListener('click', () => this.loadProcessedData());
        if (elements.exportAllBtn) elements.exportAllBtn.addEventListener('click', () => this.exportAllData());
        if (elements.validateAllBtn) elements.validateAllBtn.addEventListener('click', () => this.validateAllData());
        if (elements.clearLogsBtn) elements.clearLogsBtn.addEventListener('click', () => this.clearLogs());
        if (elements.countrySearch) elements.countrySearch.addEventListener('input', (e) => this.filterCountries(e.target.value));
        
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', () => {
                document.getElementById('validationModal').style.display = 'none';
                document.getElementById('errorModal').style.display = 'none';
                document.getElementById('successModal').style.display = 'none';
            });
        });
        
        window.addEventListener('click', (event) => {
            const modals = ['validationModal', 'errorModal', 'successModal'];
            modals.forEach(modalId => {
                const modal = document.getElementById(modalId);
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    updateStepProgress(step, current, total) {
        const stepProgress = document.getElementById('stepProgress');
        const stepName = document.getElementById('currentStepName');
        const stepCount = document.getElementById('stepCount');
        
        if (stepProgress) {
            const percent = (current / total) * 100;
            stepProgress.style.width = `${percent}%`;
        }
        if (stepName) stepName.textContent = step;
        if (stepCount) stepCount.textContent = `${current}/${total}`;
    }

    resetStepProgress() {
        const stepProgress = document.getElementById('stepProgress');
        const stepName = document.getElementById('currentStepName');
        const stepCount = document.getElementById('stepCount');
        
        if (stepProgress) stepProgress.style.width = '0%';
        if (stepName) stepName.textContent = 'Waiting...';
        if (stepCount) stepCount.textContent = '0/0';
    }

    async checkConnection() {
        try {
            const response = await fetch('http://localhost:8000/health');
            if (response.ok) {
                const data = await response.json();
                const statusElement = document.getElementById('connectionStatus');
                if (statusElement) {
                    statusElement.className = 'status-indicator connected';
                    const dot = statusElement.querySelector('.status-dot');
                    if (dot) dot.style.background = '#48bb78';
                    const span = statusElement.querySelector('span:last-child');
                    if (span) span.textContent = 'Connected';
                }
                const versionElement = document.getElementById('appVersion');
                if (versionElement) versionElement.textContent = `v${data.version}`;
                return true;
            }
        } catch (error) {
            console.error('Connection error:', error);
            const statusElement = document.getElementById('connectionStatus');
            if (statusElement) {
                statusElement.className = 'status-indicator';
                const span = statusElement.querySelector('span:last-child');
                if (span) span.textContent = 'Disconnected';
            }
        }
        return false;
    }

    startHealthCheck() {
        setInterval(() => this.checkConnection(), 30000);
    }

    async selectDataDir() {
        const dir = await window.electronAPI.selectDirectory();
        if (dir) {
            const dataDirInput = document.getElementById('dataDir');
            if (dataDirInput) dataDirInput.value = dir;
            await this.scanDirectory(dir);
        }
    }

    async scanDirectory(dir) {
        try {
            const response = await window.electronAPI.api.post('/scan', { path: dir });
            this.scanData = response;
            this.displayHierarchy(response);
            const startBtn = document.getElementById('startProcessing');
            if (startBtn) startBtn.disabled = response.total_countries === 0;
            const countSpan = document.getElementById('countriesCount');
            if (countSpan) countSpan.textContent = response.total_countries;
        } catch (error) {
            this.showError('Failed to scan directory: ' + error.message);
        }
    }

    displayHierarchy(data) {
        const container = document.getElementById('countriesList');
        if (!container) return;
        
        if (!data.data_types || data.data_types.length === 0) {
            container.innerHTML = '<div class="placeholder"><span>📁</span><p>No countries found</p></div>';
            return;
        }
        
        let html = `
            <div class="scan-summary">
                <div class="summary-card">
                    <div class="summary-icon">🌍</div>
                    <div class="summary-info">
                        <div class="summary-value">${data.total_continents}</div>
                        <div class="summary-label">Continents</div>
                    </div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">🗺️</div>
                    <div class="summary-info">
                        <div class="summary-value">${data.total_countries}</div>
                        <div class="summary-label">Countries</div>
                    </div>
                </div>
            </div>
        `;
        
        for (const dataType of data.data_types) {
            const isMap = dataType.name.includes('Map');
            html += `
                <div class="data-type-section">
                    <div class="data-type-header ${isMap ? 'map-header' : 'mapless-header'}">
                        <div class="data-type-icon">${isMap ? '🗺️' : '📄'}</div>
                        <div class="data-type-title">${dataType.name}</div>
                        <div class="data-type-stats">
                            <span class="stat-badge">${dataType.continents.length} continents</span>
                            <span class="stat-badge">${dataType.country_count} countries</span>
                        </div>
                        <div class="data-type-actions">
                            <button class="select-type-btn" data-type="${dataType.name}">Select All</button>
                        </div>
                    </div>
                    <div class="continents-container">
            `;
            
            for (const continent of dataType.continents) {
                const continentId = `continent-${dataType.name}-${continent.name}`.replace(/[^a-zA-Z0-9-]/g, '-');
                html += `
                    <div class="continent-section">
                        <div class="continent-header" onclick="window.app.toggleContinent('${continentId}')">
                            <span class="expand-icon">▶</span>
                            <span class="continent-name">${continent.name}</span>
                            <span class="continent-count">${continent.countries.length} countries</span>
                            <button class="select-continent-btn" data-type="${dataType.name}" data-continent="${continent.name}" onclick="event.stopPropagation(); window.app.selectContinent('${dataType.name}', '${continent.name}')">Select All</button>
                        </div>
                        <div id="${continentId}" class="continent-countries" style="display: none;">
                `;
                
                for (const country of continent.countries) {
                    html += `
                        <div class="country-item" data-country="${country.name}" data-type="${dataType.name}" data-continent="${continent.name}">
                            <input type="checkbox" id="country-${country.name}" value="${country.name}" 
                                   data-states="${country.states}" data-max-level="${country.max_level}"
                                   data-base-path="${country.base_path}" data-type="${dataType.name}"
                                   data-continent="${continent.name}">
                            <div class="country-info">
                                <div class="country-name">
                                    ${country.name}
                                    ${country.has_geometries ? '<span class="badge-map">Has Geometry</span>' : '<span class="badge-mapless">No Geometry</span>'}
                                </div>
                                <div class="country-meta">
                                    ${country.states} states | Level ${country.max_level}
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                html += `</div></div>`;
            }
            
            html += `</div></div>`;
        }
        
        container.innerHTML = html;
        
        document.querySelectorAll('#countriesList input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', () => this.updateSelectedCountries());
        });
        
        document.querySelectorAll('.select-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectDataType(btn.dataset.type);
            });
        });
        
        this.updateSelectedCountries();
    }

    toggleContinent(continentId) {
        const container = document.getElementById(continentId);
        if (!container) return;
        const header = container.previousElementSibling;
        const expandIcon = header?.querySelector('.expand-icon');
        
        if (container.style.display === 'none') {
            container.style.display = 'block';
            if (expandIcon) expandIcon.textContent = '▼';
        } else {
            container.style.display = 'none';
            if (expandIcon) expandIcon.textContent = '▶';
        }
    }

    selectDataType(dataType) {
        const checkboxes = document.querySelectorAll(`#countriesList input[data-type="${dataType}"]`);
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
        this.updateSelectedCountries();
    }

    selectContinent(dataType, continent) {
        const checkboxes = document.querySelectorAll(`#countriesList input[data-type="${dataType}"][data-continent="${continent}"]`);
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
        this.updateSelectedCountries();
    }

    selectAllCountries() {
        const checkboxes = document.querySelectorAll('#countriesList input[type="checkbox"]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
        this.updateSelectedCountries();
    }

    clearAllCountries() {
        document.querySelectorAll('#countriesList input[type="checkbox"]').forEach(cb => cb.checked = false);
        this.updateSelectedCountries();
    }

    updateSelectedCountries() {
        this.selectedCountries.clear();
        const checkboxes = document.querySelectorAll('#countriesList input:checked');
        checkboxes.forEach(cb => this.selectedCountries.add(cb.value));
        
        const countSpan = document.getElementById('selectedCount');
        if (countSpan) countSpan.textContent = this.selectedCountries.size;
        
        const startBtn = document.getElementById('startProcessing');
        if (startBtn) startBtn.disabled = this.selectedCountries.size === 0;
    }

    filterCountries(searchTerm) {
        const items = document.querySelectorAll('.country-item');
        items.forEach(item => {
            const countryName = item.getAttribute('data-country');
            if (countryName?.toLowerCase().includes(searchTerm.toLowerCase())) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    getSelectedCountries() {
        const checkboxes = document.querySelectorAll('#countriesList input:checked');
        return Array.from(checkboxes).map(cb => ({
            name: cb.value,
            states: parseInt(cb.dataset.states) || 1,
            max_level: parseInt(cb.dataset.maxLevel) || 4,
            base_path: cb.dataset.basePath,
            data_type: cb.dataset.type,
            continent: cb.dataset.continent
        }));
    }

    addLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logsContainer = document.getElementById('processingLogs');
        if (logsContainer) {
            const logClass = `log-${type}`;
            const logHtml = `<div class="log-entry ${logClass}"><span class="log-time">[${timestamp}]</span> <span class="log-message">${this.escapeHtml(message)}</span></div>`;
            logsContainer.insertAdjacentHTML('afterbegin', logHtml);
            
            while (logsContainer.children.length > 200) {
                logsContainer.removeChild(logsContainer.lastChild);
            }
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clearLogs() {
        const logsContainer = document.getElementById('processingLogs');
        if (logsContainer) {
            logsContainer.innerHTML = '<div class="log-placeholder">No logs yet. Start processing to see events...</div>';
        }
        this.resetStepProgress();
    }

    async startProcessing() {
        const selectedCountries = this.getSelectedCountries();
        if (selectedCountries.length === 0) {
            this.showError('Please select at least one country');
            return;
        }

        this.clearLogs();
        this.resetStepProgress();
        this.addLog(`🚀 Starting processing for ${selectedCountries.length} countries`, 'info');
        
        const outputBase = '/home/linson/workspace/dev/data/processed/Telios';
        this.addLog(`📁 Output base directory: ${outputBase}`, 'info');

        const request = {
            data_root: document.getElementById('dataDir')?.value || '',
            output_base: outputBase,
            countries: selectedCountries
        };

        try {
            const response = await window.electronAPI.api.post('/process', request);
            this.currentJob = response.job_id;
            this.addLog(`✅ Job created with ID: ${this.currentJob}`, 'success');
            this.startPolling(response.job_id);
            this.showProgress(true);
            this.showSuccess(`Processing started for ${selectedCountries.length} countries`);
        } catch (error) {
            this.addLog(`❌ Failed to start processing: ${error.message}`, 'error');
            this.showError('Failed to start processing: ' + error.message);
        }
    }

    startPolling(jobId) {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        
        this.pollingInterval = setInterval(async () => {
            try {
                const status = await window.electronAPI.api.get(`/process/${jobId}/status`);
                this.updateProgress(status);
                
                if (status.logs && status.logs.length > 0) {
                    const currentCount = this.displayedLogCount || 0;
                    const newLogs = status.logs.slice(currentCount);
                    
                    newLogs.forEach(log => {
                        this.addLog(log.message, log.level);
                        
                        // Update step progress based on log messages
                        if (log.message.includes('Step 1/3') || log.message.includes('Extracting')) {
                            this.updateStepProgress('Extracting GeoJSON data', 1, 3);
                        } else if (log.message.includes('Step 2/3') || log.message.includes('Transforming')) {
                            this.updateStepProgress('Transforming data structure', 2, 3);
                        } else if (log.message.includes('Step 3/3') || log.message.includes('Saving')) {
                            this.updateStepProgress('Saving output files', 3, 3);
                        } else if (log.message.includes('Level 0')) {
                            this.updateStepProgress('Processing Level 0 (Country)', 1, 4);
                        } else if (log.message.includes('Level 1')) {
                            this.updateStepProgress('Processing Level 1 (States)', 2, 4);
                        } else if (log.message.includes('Level 2')) {
                            this.updateStepProgress('Processing Level 2 (Districts)', 3, 4);
                        } else if (log.message.includes('Level 3')) {
                            this.updateStepProgress('Processing Level 3 (Blocks)', 4, 4);
                        } else if (log.message.includes('Level 4')) {
                            this.updateStepProgress('Processing Level 4 (Villages)', 5, 4);
                        }
                        
                        // Update current country
                        if (log.message.includes('Processing:')) {
                            const match = log.message.match(/Processing:\s*([^,\s]+)/);
                            if (match) {
                                this.currentCountry = match[1];
                                const countryElement = document.getElementById('currentCountry');
                                if (countryElement) countryElement.textContent = this.currentCountry;
                            }
                        }
                    });
                    
                    this.displayedLogCount = status.logs.length;
                }
                
                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                    
                    if (status.status === 'completed') {
                        this.updateStepProgress('Complete', 3, 3);
                        this.addLog(`🎉 Processing completed successfully!`, 'success');
                        if (status.result) {
                            this.addLog(`📊 Total records processed: ${(status.result.total_records || 0).toLocaleString()}`, 'success');
                            this.addLog(`📁 Output saved to: ${status.result.output_path}`, 'success');
                        }
                        await this.loadProcessedData();
                        this.showProgress(false);
                    } else {
                        this.addLog(`❌ Processing failed: ${status.error || 'Unknown error'}`, 'error');
                        this.showProgress(false);
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
        }, 2000);
    }

    updateProgress(status) {
        const progressBar = document.getElementById('progressBar');
        const progressPercent = document.getElementById('progressPercent');
        const progressMessage = document.getElementById('progressMessage');
        const currentCountrySpan = document.getElementById('currentCountry');
        
        if (progressBar) progressBar.style.width = `${status.progress}%`;
        if (progressPercent) progressPercent.textContent = `${status.progress}%`;
        if (progressMessage) progressMessage.textContent = status.message || `Processing... ${status.progress}% complete`;
        
        if (currentCountrySpan && status.detailed_status && status.detailed_status.current_country) {
            currentCountrySpan.textContent = status.detailed_status.current_country;
        }
    }

    showProgress(show) {
        const section = document.getElementById('progressSection');
        if (section) section.style.display = show ? 'block' : 'none';
    }

    async loadProcessedData() {
        try {
            const countries = await window.electronAPI.api.get('/countries');
            this.processedCountries = countries;
            this.displayProcessedCountries(countries);
            this.updateStats(countries);
            this.addLog(`📊 Loaded ${countries.length} processed countries from database`, 'info');
        } catch (error) {
            console.error('Failed to load processed data:', error);
        }
    }

    updateStats(countries) {
        const totalCountries = countries.length;
        const totalRecords = countries.reduce((sum, c) => sum + (c.record_count || 0), 0);
        
        const totalCountriesEl = document.getElementById('totalCountries');
        const totalRecordsEl = document.getElementById('totalRecords');
        const validCountriesEl = document.getElementById('validCountries');
        
        if (totalCountriesEl) totalCountriesEl.textContent = totalCountries;
        if (totalRecordsEl) totalRecordsEl.textContent = totalRecords.toLocaleString();
        if (validCountriesEl) validCountriesEl.textContent = totalCountries;
    }

    displayProcessedCountries(countries) {
        const tbody = document.querySelector('#processedCountries tbody');
        if (!tbody) return;
        
        if (!countries || countries.length === 0) {
            tbody.innerHTML = '先生<td colspan="6"><div class="placeholder"><span>📊</span><p>No processed data yet</p></div></td></tr>';
            return;
        }

        tbody.innerHTML = countries.map(country => `
            <tr>
                <td><strong>${this.escapeHtml(country.country || 'Unknown')}</strong></td>
                <td>${this.escapeHtml(country.country_code || '---')}</td>
                <td>${(country.record_count || 0).toLocaleString()}</td>
                <td>${country.min_id || 0} - ${country.max_id || 0}</td>
                <td><span class="status-badge status-valid">✓ Valid</span></td>
                <td>
                    <button class="btn-outline" onclick="window.app.validateCountry('${country.country}')">Validate</button>
                    <button class="btn-outline" onclick="window.app.exportCountry('${country.country}')">Export</button>
                </td>
            </tr>
        `).join('');
    }

    async validateCountry(countryName) {
        this.addLog(`🔍 Validating ${countryName}...`, 'info');
        try {
            const results = await window.electronAPI.api.get(`/validate/${encodeURIComponent(countryName)}`);
            this.addLog(`✅ Validation complete for ${countryName}: ${results.valid ? 'PASSED' : 'FAILED'}`, results.valid ? 'success' : 'error');
            if (!results.valid) {
                this.addLog(`   ⚠️ Orphans: ${results.orphaned_records}, Hierarchy: ${results.hierarchy_issues}, Duplicates: ${results.duplicate_keys}`, 'warning');
            }
            this.showValidationResults(results);
        } catch (error) {
            this.addLog(`❌ Validation failed for ${countryName}: ${error.message}`, 'error');
            this.showError('Validation failed: ' + error.message);
        }
    }

    async validateAllData() {
        if (!this.processedCountries || this.processedCountries.length === 0) {
            this.showError('No countries to validate');
            return;
        }
        
        this.addLog(`🔍 Starting validation for all ${this.processedCountries.length} countries...`, 'info');
        this.showProgress(true);
        let results = [];
        
        for (const country of this.processedCountries) {
            if (country.country) {
                try {
                    const result = await window.electronAPI.api.get(`/validate/${encodeURIComponent(country.country)}`);
                    results.push(result);
                    this.addLog(`   ${country.country}: ${result.valid ? '✓ Valid' : '✗ Invalid'}`, result.valid ? 'success' : 'error');
                } catch (error) {
                    this.addLog(`   ${country.country}: Validation failed - ${error.message}`, 'error');
                }
            }
        }
        
        this.showProgress(false);
        this.showBulkValidationResults(results);
        const validCount = results.filter(r => r.valid).length;
        this.addLog(`✅ Validation complete: ${validCount}/${results.length} countries valid`, 'success');
    }

    showValidationResults(results) {
        const modal = document.getElementById('validationModal');
        const content = document.getElementById('validationContent');
        if (!modal || !content) return;
        
        const validText = results.valid ? '✓ VALID' : '✗ INVALID';
        
        content.innerHTML = `
            <h4>Validation Results for ${results.country}</h4>
            <div style="margin: 16px 0;">
                <div style="padding: 12px; background: #f7fafc; border-radius: 8px; margin-bottom: 8px;">
                    <strong>Orphaned Records:</strong> ${results.orphaned_records}
                </div>
                <div style="padding: 12px; background: #f7fafc; border-radius: 8px; margin-bottom: 8px;">
                    <strong>Hierarchy Issues:</strong> ${results.hierarchy_issues}
                </div>
                <div style="padding: 12px; background: #f7fafc; border-radius: 8px; margin-bottom: 8px;">
                    <strong>Duplicate Keys:</strong> ${results.duplicate_keys}
                </div>
                <div style="padding: 12px; background: ${results.valid ? '#c6f6d5' : '#fed7d7'}; border-radius: 8px; font-weight: bold;">
                    Overall Status: ${validText}
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }

    showBulkValidationResults(results) {
        const modal = document.getElementById('validationModal');
        const content = document.getElementById('validationContent');
        if (!modal || !content) return;
        
        const validCount = results.filter(r => r.valid).length;
        const invalidCount = results.length - validCount;
        
        const summary = results.map(r => `
            <div style="padding: 12px; background: ${r.valid ? '#f0f9f0' : '#fff0f0'}; border-radius: 8px; margin-bottom: 8px;">
                <strong>${r.country}</strong>
                <span style="float: right; color: ${r.valid ? '#48bb78' : '#f56565'}">
                    ${r.valid ? '✓ Valid' : '✗ Invalid'}
                </span>
                <div style="font-size: 12px; margin-top: 8px;">
                    Orphans: ${r.orphaned_records} | Hierarchy: ${r.hierarchy_issues} | Duplicates: ${r.duplicate_keys}
                </div>
            </div>
        `).join('');
        
        content.innerHTML = `
            <h4>Bulk Validation Results</h4>
            <div style="margin: 16px 0; padding: 16px; background: #f7fafc; border-radius: 8px;">
                <div>Total Countries: ${results.length}</div>
                <div style="color: #48bb78;">Valid: ${validCount}</div>
                <div style="color: #f56565;">Invalid: ${invalidCount}</div>
            </div>
            <div style="max-height: 400px; overflow-y: auto;">
                ${summary}
            </div>
        `;
        
        modal.style.display = 'block';
    }

    async exportCountry(countryName) {
        const format = document.getElementById('exportFormat')?.value || 'csv';
        try {
            this.addLog(`📤 Exporting ${countryName} as ${format.toUpperCase()}...`, 'info');
            const filePath = await window.electronAPI.saveFile({
                title: 'Save Export',
                defaultPath: `${countryName}_export.${format}`,
                filters: [{ name: format.toUpperCase(), extensions: [format] }]
            });
            
            if (filePath) {
                const response = await fetch(`http://localhost:8000/api/v1/export/${encodeURIComponent(countryName)}?format=${format}`);
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${countryName}_export.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                this.addLog(`✅ Exported ${countryName} to ${filePath}`, 'success');
                this.showSuccess(`Exported ${countryName} as ${format.toUpperCase()}`);
            }
        } catch (error) {
            this.addLog(`❌ Export failed for ${countryName}: ${error.message}`, 'error');
            this.showError('Export failed: ' + error.message);
        }
    }

    async exportAllData() {
        if (!this.processedCountries || this.processedCountries.length === 0) {
            this.showError('No data to export');
            return;
        }
        
        const format = document.getElementById('exportFormat')?.value || 'csv';
        this.addLog(`📤 Exporting all ${this.processedCountries.length} countries as ${format.toUpperCase()}...`, 'info');
        this.showProgress(true);
        
        for (const country of this.processedCountries) {
            if (country.country) {
                await this.exportCountry(country.country);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
        
        this.showProgress(false);
        this.addLog(`✅ Completed export of ${this.processedCountries.length} countries`, 'success');
        this.showSuccess(`Exported ${this.processedCountries.length} countries as ${format.toUpperCase()}`);
    }

    async refreshScan() {
        const dir = document.getElementById('dataDir')?.value;
        if (dir) {
            await this.scanDirectory(dir);
        } else {
            await this.selectDataDir();
        }
    }

    showError(message) {
        const modal = document.getElementById('errorModal');
        const content = document.getElementById('errorContent');
        if (modal && content) {
            content.innerHTML = `<p>${this.escapeHtml(message)}</p>`;
            modal.style.display = 'block';
            
            setTimeout(() => {
                if (modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            }, 5000);
        } else {
            alert('Error: ' + message);
        }
    }

    showSuccess(message) {
        const modal = document.getElementById('successModal');
        const content = document.getElementById('successContent');
        if (modal && content) {
            content.innerHTML = `<p>${this.escapeHtml(message)}</p>`;
            modal.style.display = 'block';
            
            setTimeout(() => {
                if (modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            }, 3000);
        } else {
            alert('Success: ' + message);
        }
    }
}

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new TeliosGeoProcessor();
    window.app = app;
});
