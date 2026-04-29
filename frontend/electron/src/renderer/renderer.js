// State management
let currentJobId = null;
let mapCountries = [];
let maplessCountries = [];
let selectedCountries = new Set(); // Store unique keys like "India_Map" or "India_Mapless"
let isProcessing = false;
let statusCheckInterval = null;

// DOM Elements
const dataRootInput = document.getElementById('dataRoot');
const outputBaseInput = document.getElementById('outputBase');
const browseBtn = document.getElementById('browseBtn');
const browseOutputBtn = document.getElementById('browseOutputBtn');
const scanBtn = document.getElementById('scanBtn');
const processBtn = document.getElementById('processBtn');
const selectAllMap = document.getElementById('selectAllMap');
const selectAllMapless = document.getElementById('selectAllMapless');
const mapCountriesList = document.getElementById('mapCountriesList');
const maplessCountriesList = document.getElementById('maplessCountriesList');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const statusMessage = document.getElementById('statusMessage');
const currentOperation = document.getElementById('currentOperation');
const logsContainer = document.getElementById('logsContainer');
const resultsSection = document.getElementById('resultsSection');
const resultsSummary = document.getElementById('resultsSummary');
const resultsDetails = document.getElementById('resultsDetails');
const clearLogsBtn = document.getElementById('clearLogsBtn');
const selectedCountSpan = document.getElementById('selectedCount');
const selectedMapCountSpan = document.getElementById('selectedMapCount');
const selectedMaplessCountSpan = document.getElementById('selectedMaplessCount');
const mapCountSpan = document.getElementById('mapCount');
const maplessCountSpan = document.getElementById('maplessCount');

// API Base URL
const API_BASE = 'http://localhost:8000/api/v1';

// Add log message
function addLog(message, level = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    const timestamp = new Date().toLocaleTimeString();
    logEntry.textContent = `[${timestamp}] ${message}`;
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
    
    while (logsContainer.children.length > 200) {
        logsContainer.removeChild(logsContainer.firstChild);
    }
}

// Clear logs
clearLogsBtn.addEventListener('click', () => {
    logsContainer.innerHTML = '';
    addLog('Logs cleared', 'info');
});

// Update selection counts
function updateSelectionCounts() {
    const mapSelected = Array.from(selectedCountries).filter(key => key.endsWith('_Map')).length;
    const maplessSelected = Array.from(selectedCountries).filter(key => key.endsWith('_Mapless')).length;
    
    selectedMapCountSpan.textContent = mapSelected;
    selectedMaplessCountSpan.textContent = maplessSelected;
    selectedCountSpan.textContent = selectedCountries.size;
    
    // Update select all checkboxes
    if (mapCountries.length > 0) {
        const allMapSelected = mapCountries.every(c => selectedCountries.has(`${c.name}_Map`));
        selectAllMap.checked = allMapSelected;
        selectAllMap.indeterminate = !allMapSelected && mapSelected > 0;
    }
    
    if (maplessCountries.length > 0) {
        const allMaplessSelected = maplessCountries.every(c => selectedCountries.has(`${c.name}_Mapless`));
        selectAllMapless.checked = allMaplessSelected;
        selectAllMapless.indeterminate = !allMaplessSelected && maplessSelected > 0;
    }
    
    updateProcessButtonState();
}

// Update process button state
function updateProcessButtonState() {
    if (isProcessing) {
        processBtn.disabled = true;
        processBtn.textContent = '⏳ Processing...';
    } else {
        const hasSelected = selectedCountries.size > 0;
        processBtn.disabled = !hasSelected;
        processBtn.textContent = hasSelected ? '▶ Start Processing' : '⏸ Select Countries to Process';
    }
}

// Update progress
function updateProgress(progress, message, operation = '') {
    const percentage = Math.floor(progress);
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `${percentage}%`;
    statusMessage.textContent = message;
    if (operation) {
        currentOperation.textContent = operation;
    }
    
    if (percentage >= 100) {
        progressBar.style.background = 'linear-gradient(90deg, #4caf50, #8bc34a)';
    } else if (percentage >= 75) {
        progressBar.style.background = 'linear-gradient(90deg, #ff9800, #ffc107)';
    } else {
        progressBar.style.background = 'linear-gradient(90deg, #2196f3, #03a9f4)';
    }
}

// Check job status periodically
async function checkJobStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`${API_BASE}/process/${currentJobId}/status`);
        const status = await response.json();
        
        if (status.logs && status.logs.length > 0) {
            status.logs.forEach(log => {
                addLog(log.message, log.level);
            });
        }
        
        if (status.progress !== undefined) {
            updateProgress(status.progress, status.message || 'Processing...', status.current_operation || '');
        }
        
        if (status.status === 'completed') {
            stopProcessing();
            addLog('✅ Processing completed successfully!', 'success');
            updateProgress(100, 'Processing complete!', 'All done!');
            displayResults(status.result);
            scanBtn.disabled = false;
            
        } else if (status.status === 'failed') {
            stopProcessing();
            addLog(`❌ Processing failed: ${status.error || 'Unknown error'}`, 'error');
            updateProgress(0, 'Processing failed', '');
            scanBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('Error checking job status:', error);
        addLog(`Error checking status: ${error.message}`, 'error');
    }
}

// Display processing results
function displayResults(result) {
    resultsSection.style.display = 'block';
    
    if (!result) {
        resultsSummary.innerHTML = '<p>No results available</p>';
        return;
    }
    
    let summaryHtml = `
        <h3>📊 Processing Summary</h3>
        <p><strong>Total Records:</strong> ${(result.total_records || 0).toLocaleString()}</p>
        <p><strong>Countries Processed:</strong> ${result.countries_processed || 0}</p>
        <p><strong>Output Path:</strong> ${result.output_path || 'N/A'}</p>
    `;
    
    if (result.map_output) {
        summaryHtml += `<p><strong>🗺️ Map Output:</strong> ${result.map_output}</p>`;
    }
    if (result.mapless_output) {
        summaryHtml += `<p><strong>📄 Mapless Output:</strong> ${result.mapless_output}</p>`;
    }
    
    resultsSummary.innerHTML = summaryHtml;
    
    if (result.results && result.results.length > 0) {
        const mapResults = result.results.filter(r => r.data_type === 'Map');
        const maplessResults = result.results.filter(r => r.data_type === 'Mapless');
        
        let detailsHtml = '<h3>📋 Country Details</h3>';
        
        if (mapResults.length > 0) {
            detailsHtml += '<h4>🗺️ Map Data</h4><table class="results-table"><thead>脂肪<th>Country</th><th>Records</th><th>Processing Time</th></thead><tbody>';
            mapResults.forEach(r => {
                detailsHtml += `<tr><td>${r.country}</td><td>${(r.record_count || 0).toLocaleString()}</td><td>${r.processing_time ? r.processing_time.toFixed(1) + 's' : 'N/A'}</td></tr>`;
            });
            detailsHtml += '</tbody></table>';
        }
        
        if (maplessResults.length > 0) {
            detailsHtml += '<h4>📄 Mapless Data</h4><table class="results-table"><thead>脂肪<th>Country</th><th>Records</th><th>Processing Time</th></thead><tbody>';
            maplessResults.forEach(r => {
                detailsHtml += `<tr><td>${r.country}</td><td>${(r.record_count || 0).toLocaleString()}</td><td>${r.processing_time ? r.processing_time.toFixed(1) + 's' : 'N/A'}</td></tr>`;
            });
            detailsHtml += '</tbody></table>';
        }
        
        resultsDetails.innerHTML = detailsHtml;
    }
}

// Start processing
async function startProcessing() {
    if (isProcessing) {
        addLog('⚠️ Processing already in progress', 'warning');
        return;
    }
    
    const dataRoot = dataRootInput.value.trim();
    const outputBase = outputBaseInput.value.trim();
    
    if (!dataRoot) {
        addLog('❌ Please enter a data root directory', 'error');
        return;
    }
    
    if (!outputBase) {
        addLog('❌ Please enter an output directory', 'error');
        return;
    }
    
    if (selectedCountries.size === 0) {
        addLog('❌ Please select at least one country to process', 'error');
        return;
    }
    
    // Prepare countries list from unique keys
    const countries = [];
    
    for (const selectedKey of selectedCountries) {
        // Parse the key: "India_Map" or "India_Mapless"
        const lastUnderscore = selectedKey.lastIndexOf('_');
        const countryName = selectedKey.substring(0, lastUnderscore);
        const dataType = selectedKey.substring(lastUnderscore + 1);
        
        let countryInfo = null;
        
        if (dataType === 'Map') {
            countryInfo = mapCountries.find(c => c.name === countryName);
        } else if (dataType === 'Mapless') {
            countryInfo = maplessCountries.find(c => c.name === countryName);
        }
        
        if (countryInfo) {
            countries.push({
                name: countryInfo.name,
                base_path: countryInfo.base_path,
                continent: countryInfo.continent,
                data_type: dataType,
                states: countryInfo.states,
                max_level: countryInfo.max_level,
                countryId: countryInfo.countryId || 0
            });
            addLog(`📌 Added: ${countryInfo.name} (${dataType}) - ${countryInfo.states} states, Level ${countryInfo.max_level}`, 'info');
        } else {
            addLog(`⚠️ Country not found: ${countryName} (${dataType})`, 'warning');
        }
    }
    
    if (countries.length === 0) {
        addLog('❌ No valid countries to process', 'error');
        return;
    }
    
    const requestData = {
        data_root: dataRoot,
        output_base: outputBase,
        countries: countries
    };
    
    isProcessing = true;
    updateProcessButtonState();
    scanBtn.disabled = true;
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
    const mapCount = countries.filter(c => c.data_type === 'Map').length;
    const maplessCount = countries.filter(c => c.data_type === 'Mapless').length;
    
    addLog(`🚀 Starting processing...`, 'info');
    addLog(`🗺️ Map countries: ${mapCount}`, 'info');
    addLog(`📄 Mapless countries: ${maplessCount}`, 'info');
    addLog(`📁 Data root: ${dataRoot}`, 'info');
    addLog(`💾 Output: ${outputBase}`, 'info');
    
    try {
        const response = await fetch(`${API_BASE}/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        addLog(`✅ Job started with ID: ${currentJobId}`, 'success');
        
        if (statusCheckInterval) clearInterval(statusCheckInterval);
        statusCheckInterval = setInterval(checkJobStatus, 2000);
        
    } catch (error) {
        addLog(`❌ Failed to start processing: ${error.message}`, 'error');
        stopProcessing();
    }
}

// Stop processing
function stopProcessing() {
    isProcessing = false;
    currentJobId = null;
    updateProcessButtonState();
    scanBtn.disabled = false;
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

// Display countries by category
function displayCountries() {
    // Display Map countries
    if (mapCountries.length === 0) {
        mapCountriesList.innerHTML = '<div class="loading">No Map data found</div>';
        mapCountSpan.textContent = '0 countries';
    } else {
        mapCountSpan.textContent = `${mapCountries.length} countries`;
        let html = '';
        mapCountries.forEach(country => {
            const uniqueKey = `${country.name}_Map`;
            const isSelected = selectedCountries.has(uniqueKey);
            const pathParts = country.base_path.split('/');
            const folderHint = pathParts.slice(-3).join('/');
            
            html += `
                <div class="country-item ${isSelected ? 'selected' : ''}" data-unique-key="${uniqueKey}" data-country="${country.name}" data-type="Map">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} data-unique-key="${uniqueKey}">
                    <span class="country-name">${country.name}</span>
                    <div class="country-details">
                        <span class="data-badge map-badge">🗺️ Map</span>
                        <span>${country.continent || 'N/A'}</span>
                        <span>${country.states || 0} states</span>
                        <span>L${country.max_level || 4}</span>
                        <span class="path-hint">📁 ${folderHint}</span>
                    </div>
                </div>
            `;
        });
        mapCountriesList.innerHTML = html;
    }
    
    // Display Mapless countries
    if (maplessCountries.length === 0) {
        maplessCountriesList.innerHTML = '<div class="loading">No Mapless data found</div>';
        maplessCountSpan.textContent = '0 countries';
    } else {
        maplessCountSpan.textContent = `${maplessCountries.length} countries`;
        let html = '';
        maplessCountries.forEach(country => {
            const uniqueKey = `${country.name}_Mapless`;
            const isSelected = selectedCountries.has(uniqueKey);
            const pathParts = country.base_path.split('/');
            const folderHint = pathParts.slice(-3).join('/');
            
            html += `
                <div class="country-item ${isSelected ? 'selected' : ''}" data-unique-key="${uniqueKey}" data-country="${country.name}" data-type="Mapless">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} data-unique-key="${uniqueKey}">
                    <span class="country-name">${country.name}</span>
                    <div class="country-details">
                        <span class="data-badge mapless-badge">📄 Mapless</span>
                        <span>${country.continent || 'N/A'}</span>
                        <span>${country.states || 0} states</span>
                        <span>L${country.max_level || 4}</span>
                        <span class="path-hint">📁 ${folderHint}</span>
                    </div>
                </div>
            `;
        });
        maplessCountriesList.innerHTML = html;
    }
    
    // Add event listeners with unique keys
    document.querySelectorAll('#mapCountriesList .country-item, #maplessCountriesList .country-item').forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        const uniqueKey = item.dataset.uniqueKey;
        const countryName = item.dataset.country;
        const dataType = item.dataset.type;
        
        const toggleSelection = () => {
            if (checkbox.checked) {
                selectedCountries.add(uniqueKey);
                item.classList.add('selected');
                addLog(`✅ Selected: ${countryName} (${dataType}) - Path: ${item.querySelector('.path-hint')?.textContent || ''}`, 'success');
            } else {
                selectedCountries.delete(uniqueKey);
                item.classList.remove('selected');
                addLog(`❌ Deselected: ${countryName} (${dataType})`, 'info');
            }
            updateSelectionCounts();
        };
        
        checkbox.addEventListener('change', toggleSelection);
        item.addEventListener('click', (e) => {
            if (e.target !== checkbox && !e.target.classList.contains('path-hint')) {
                checkbox.checked = !checkbox.checked;
                toggleSelection();
            }
        });
    });
    
    updateSelectionCounts();
}

// Scan for countries
async function scanCountries() {
    const dataRoot = dataRootInput.value.trim();
    
    if (!dataRoot) {
        addLog('❌ Please enter a data root directory', 'error');
        return;
    }
    
    addLog(`🔍 Scanning directory: ${dataRoot}`, 'info');
    mapCountriesList.innerHTML = '<div class="loading">Scanning Map folder...</div>';
    maplessCountriesList.innerHTML = '<div class="loading">Scanning Mapless folder...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: dataRoot })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Reset data
        mapCountries = [];
        maplessCountries = [];
        selectedCountries.clear();
        
        // Process scan results
        data.data_types.forEach(dataType => {
            dataType.continents.forEach(continent => {
                continent.countries.forEach(country => {
                    const countryInfo = {
                        ...country,
                        continent: continent.name,
                        data_type: dataType.type
                    };
                    
                    if (dataType.type === 'Map') {
                        mapCountries.push(countryInfo);
                    } else {
                        maplessCountries.push(countryInfo);
                    }
                });
            });
        });
        
        displayCountries();
        
        addLog(`✅ Scan complete!`, 'success');
        addLog(`🗺️ Map: ${mapCountries.length} countries`, 'success');
        addLog(`📄 Mapless: ${maplessCountries.length} countries`, 'success');
        
        // Log details for duplicates
        const mapNames = mapCountries.map(c => c.name);
        const maplessNames = maplessCountries.map(c => c.name);
        const duplicates = mapNames.filter(name => maplessNames.includes(name));
        
        if (duplicates.length > 0) {
            addLog(`⚠️ Note: ${duplicates.join(', ')} appear in BOTH Map and Mapless folders`, 'warning');
            addLog(`   Select carefully - each version shows its folder path`, 'info');
        }
        
        const scanStatus = document.getElementById('scanStatus');
        scanStatus.className = 'status-badge success';
        scanStatus.textContent = `✅ Found ${mapCountries.length} Map | ${maplessCountries.length} Mapless countries`;
        
    } catch (error) {
        addLog(`❌ Scan failed: ${error.message}`, 'error');
        mapCountriesList.innerHTML = `<div class="loading error">Error: ${error.message}</div>`;
        maplessCountriesList.innerHTML = `<div class="loading error">Error: ${error.message}</div>`;
        
        const scanStatus = document.getElementById('scanStatus');
        scanStatus.className = 'status-badge error';
        scanStatus.textContent = `❌ Scan failed: ${error.message}`;
    }
}

// Select all in category
selectAllMap.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    mapCountries.forEach(country => {
        const uniqueKey = `${country.name}_Map`;
        if (isChecked) {
            selectedCountries.add(uniqueKey);
        } else {
            selectedCountries.delete(uniqueKey);
        }
    });
    displayCountries();
    updateSelectionCounts();
    addLog(`${isChecked ? 'Selected' : 'Deselected'} all Map countries (${mapCountries.length})`, 'info');
});

selectAllMapless.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    maplessCountries.forEach(country => {
        const uniqueKey = `${country.name}_Mapless`;
        if (isChecked) {
            selectedCountries.add(uniqueKey);
        } else {
            selectedCountries.delete(uniqueKey);
        }
    });
    displayCountries();
    updateSelectionCounts();
    addLog(`${isChecked ? 'Selected' : 'Deselected'} all Mapless countries (${maplessCountries.length})`, 'info');
});

// Browse for directory
browseBtn.addEventListener('click', async () => {
    try {
        const result = await window.electronAPI.openDirectory();
        if (result && !result.canceled && result.filePaths && result.filePaths[0]) {
            dataRootInput.value = result.filePaths[0];
        }
    } catch (error) {
        console.error('Browse error:', error);
        addLog(`Browse error: ${error.message}`, 'error');
    }
});

browseOutputBtn.addEventListener('click', async () => {
    try {
        const result = await window.electronAPI.openDirectory();
        if (result && !result.canceled && result.filePaths && result.filePaths[0]) {
            outputBaseInput.value = result.filePaths[0];
        }
    } catch (error) {
        console.error('Browse error:', error);
        addLog(`Browse error: ${error.message}`, 'error');
    }
});

// Event listeners
scanBtn.addEventListener('click', scanCountries);
processBtn.addEventListener('click', startProcessing);

// Auto-scan on load
async function autoScan() {
    addLog('🔄 Auto-scanning with default paths...', 'info');
    await scanCountries();
}

// Initialize
addLog('✅ Telios GeoProcessor ready', 'success');
addLog('📡 Connected to backend at http://localhost:8000', 'info');
addLog('📁 Default Data Root: /home/linson/workspace/dev/data/raw/Telios', 'info');
addLog('💾 Default Output: /home/linson/workspace/dev/data/processed/Telios', 'info');
addLog('🔍 Auto-scanning for Map and Mapless data...', 'info');

// Auto-scan after 1 second to allow UI to load
setTimeout(() => {
    autoScan();
}, 1000);

// Save paths on change
dataRootInput.addEventListener('change', () => {
    localStorage.setItem('dataRoot', dataRootInput.value);
});
outputBaseInput.addEventListener('change', () => {
    localStorage.setItem('outputBase', outputBaseInput.value);
});
