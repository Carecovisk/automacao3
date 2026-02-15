let currentFileData = null;
let currentFileName = null;
let currentFullData = null; // Store full data including skipped rows

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const columnSelection = document.getElementById('columnSelection');
const submitBtn = document.getElementById('submitBtn');
const statusDiv = document.getElementById('status');

// Click to upload
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Drag and drop handlers
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('bg-green-100');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('bg-green-100');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('bg-green-100');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        processFile(file);
    }
});

// File input change handler
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        processFile(file);
    }
});

// Process the Excel file
function processFile(file) {
    // Validate file type
    const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
        showStatus('Erro: Por favor, selecione um arquivo Excel válido (.xlsx ou .xls)', 'error');
        return;
    }
    
    currentFileName = file.name;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            
            // Get the first sheet
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            
            // Convert to JSON
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            
            if (jsonData.length === 0) {
                showStatus('Erro: O arquivo está vazio', 'error');
                return;
            }
            
            currentFullData = jsonData;
            currentFileData = jsonData;
            
            // Get column names (first row by default)
            const skipRows = 0;
            const columns = jsonData[skipRows];
            
            // Update file info
            document.getElementById('fileName').textContent = currentFileName;
            document.getElementById('rowCount').textContent = jsonData.length - 1 - skipRows; // Exclude header and skipped rows
            document.getElementById('colCount').textContent = columns.length;
            document.getElementById('skipRows').value = skipRows;
            
            // Populate column selectors
            populateColumnSelectors(columns);
            
            // Show column selection section
            columnSelection.classList.remove('hidden');
            
            showStatus('Arquivo carregado com sucesso! Agora selecione as colunas.', 'success');
            
        } catch (error) {
            showStatus('Erro ao processar arquivo: ' + error.message, 'error');
            console.error('Error processing file:', error);
        }
    };
    
    reader.onerror = () => {
        showStatus('Erro ao ler o arquivo', 'error');
    };
    
    reader.readAsArrayBuffer(file);
}

// Populate column selectors with available columns
function populateColumnSelectors(columns) {
    const selectors = ['descriptionCol', 'valueCol', 'quantityCol'];
    
    selectors.forEach(selectorId => {
        const selector = document.getElementById(selectorId);
        // Clear existing options except the first one
        selector.innerHTML = '<option value="">-- Selecione a coluna --</option>';
        
        // Add column options
        columns.forEach((col, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = col || `Coluna ${index + 1}`;
            selector.appendChild(option);
        });
    });
}

// Handle skip rows change
document.getElementById('skipRows').addEventListener('change', function() {
    if (!currentFullData) return;
    
    const skipRows = parseInt(this.value) || 0;
    
    if (skipRows >= currentFullData.length) {
        showStatus('Erro: Número de linhas a pular excede o total de linhas', 'error');
        this.value = 0;
        return;
    }
    
    // Update current data starting from skip row
    currentFileData = currentFullData.slice(skipRows);
    
    // Get new column names
    const columns = currentFileData[0];
    
    // Update row count
    document.getElementById('rowCount').textContent = currentFileData.length - 1;
    
    // Repopulate column selectors
    populateColumnSelectors(columns);
    
    // Reset selections
    document.getElementById('descriptionCol').value = '';
    document.getElementById('valueCol').value = '';
    document.getElementById('quantityCol').value = '';
    submitBtn.disabled = true;
    
    showStatus('Colunas atualizadas com base nas linhas puladas', 'success');
});

// Enable submit button when all columns are selected
document.getElementById('descriptionCol').addEventListener('change', checkFormValidity);
document.getElementById('valueCol').addEventListener('change', checkFormValidity);
document.getElementById('quantityCol').addEventListener('change', checkFormValidity);

function checkFormValidity() {
    const descCol = document.getElementById('descriptionCol').value;
    const valCol = document.getElementById('valueCol').value;
    const qtyCol = document.getElementById('quantityCol').value;
    
    // Check if all are selected and different
    if (descCol && valCol && qtyCol) {
        // Check for duplicates
        const uniqueValues = new Set([descCol, valCol, qtyCol]);
        if (uniqueValues.size === 3) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
            showStatus('Erro: Selecione colunas diferentes para cada campo', 'error');
        }
    } else {
        submitBtn.disabled = true;
    }
}

// Handle form submission
submitBtn.addEventListener('click', async () => {
    if (!currentFileData) {
        showStatus('Erro: Nenhum arquivo carregado', 'error');
        return;
    }
    
    const descCol = parseInt(document.getElementById('descriptionCol').value);
    const valCol = parseInt(document.getElementById('valueCol').value);
    const qtyCol = parseInt(document.getElementById('quantityCol').value);
    const skipRows = parseInt(document.getElementById('skipRows').value) || 0;
    
    // Extract data with selected columns
    const headers = currentFileData[0];
    const processedData = {
        fileName: currentFileName,
        skipRows: skipRows,
        columns: {
            description: headers[descCol],
            value: headers[valCol],
            quantity: headers[qtyCol]
        },
        columnIndices: {
            description: descCol,
            value: valCol,
            quantity: qtyCol
        },
        data: currentFileData.slice(1).map(row => ({
            description: row[descCol],
            value: row[valCol],
            quantity: row[qtyCol]
        }))
    };
    
    try {
        submitBtn.disabled = true;
        showStatus('Enviando dados...', 'success');
        
        const response = await fetch('/api/process-excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processedData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showStatus('Dados processados com sucesso!', 'success');
            console.log('Resultado:', result);
            
            // Reset form after 2 seconds
            setTimeout(() => {
                resetForm();
            }, 2000);
        } else {
            const error = await response.text();
            showStatus('Erro ao processar: ' + error, 'error');
            submitBtn.disabled = false;
        }
    } catch (error) {
        showStatus('Erro ao enviar dados: ' + error.message, 'error');
        submitBtn.disabled = false;
        console.error('Error:', error);
    }
});

// Show status message
function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.classList.remove('hidden', 'bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800');
    
    if (type === 'success') {
        statusDiv.classList.add('bg-green-100', 'text-green-800');
    } else if (type === 'error') {
        statusDiv.classList.add('bg-red-100', 'text-red-800');
    }
}

// Reset form
function resetForm() {
    currentFileData = null;
    currentFileName = null;
    currentFullData = null;
    fileInput.value = '';
    columnSelection.classList.add('hidden');
    statusDiv.classList.add('hidden');
    submitBtn.disabled = true;
    
    // Reset selectors
    document.getElementById('descriptionCol').value = '';
    document.getElementById('valueCol').value = '';
    document.getElementById('quantityCol').value = '';
    document.getElementById('skipRows').value = '0';
}
