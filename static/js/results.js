// Results page - handles polling for task status and displaying results

let taskId = null;
let pollingInterval = null;
let resultsData = null;

// Extract task ID from URL parameters on page load
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    taskId = urlParams.get('taskId');
    
    if (!taskId) {
        showError('Task ID não encontrado. Por favor, inicie o processo novamente.');
        return;
    }
    
    // Start polling
    startPolling();
});

// Start polling for task status
function startPolling() {
    if (!taskId) {
        showError('Task ID inválido');
        return;
    }
    
    // Poll immediately
    pollTaskStatus();
    
    // Then poll every 2 seconds
    pollingInterval = setInterval(pollTaskStatus, 2000);
}

// Stop polling
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Poll task status from server
async function pollTaskStatus() {
    try {
        const response = await fetch(`/api/task-status/${taskId}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                showError('Task não encontrada. Pode ter expirado.');
                stopPolling();
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        updateUI(data);
        
        // Stop polling if completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
            stopPolling();
        }
        
    } catch (error) {
        console.error('Erro ao buscar status:', error);
        showError(`Erro ao buscar status: ${error.message}`);
        stopPolling();
    }
}

// Update UI based on task status
function updateUI(data) {
    const { status, progress, total, percentage, results, error, stage, message } = data;
    
    // Update progress bar
    const progressBar = document.getElementById('progressBar');
    const percentageText = document.getElementById('percentageText');
    const progressText = document.getElementById('progressText');
    const statusText = document.getElementById('statusText');
    const stageText = document.getElementById('stageText');
    const messageText = document.getElementById('messageText');
    
    if (progressBar && percentage !== undefined) {
        progressBar.style.width = `${percentage}%`;
    }
    
    if (percentageText) {
        percentageText.textContent = `${percentage.toFixed(1)}%`;
    }
    
    if (progressText && progress !== undefined && total !== undefined) {
        progressText.textContent = `${progress} / ${total}`;
    }
    
    // Update status text
    const statusMap = {
        'pending': 'Aguardando início...',
        'running': 'Processando...',
        'completed': 'Concluído!',
        'failed': 'Falhou'
    };
    
    if (statusText) {
        statusText.textContent = statusMap[status] || status;
        statusText.className = `text-sm font-medium ${
            status === 'completed' ? 'text-green-600' :
            status === 'failed' ? 'text-red-600' :
            'text-blue-600'
        }`;
    }
    
    // Update stage text
    if (stageText && stage) {
        const stageMap = {
            'initializing': 'Inicializando...',
            'preprocessing': 'Pré-processando documentos...',
            'llm_replacements': 'Obtendo replacements do LLM...',
            'creating_db': 'Criando banco de dados vetorial...',
            'inserting_db': 'Inserindo documentos no banco vetorial...',
            'querying_db': 'Consultando documentos relevantes...',
            'reranking': 'Reordenando resultados...'
        };
        stageText.textContent = stageMap[stage] || stage;
    }

    // Update arbitrary message
    if (messageText) {
        messageText.textContent = message || '';
    }
    
    // Handle completion
    if (status === 'completed' && results) {
        displayResults(results);
    }
    
    // Handle error
    if (status === 'failed' && error) {
        showError(error);
    }
}

// Display results in table
function displayResults(results) {
    resultsData = results;
    
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const resultsCount = document.getElementById('resultsCount');
    const resultsBody = document.getElementById('resultsBody');
    
    // Hide progress, show results
    if (progressSection) {
        progressSection.classList.add('hidden');
    }
    if (resultsSection) {
        resultsSection.classList.remove('hidden');
    }
    
    // Update count
    if (resultsCount) {
        resultsCount.textContent = `${results.length} correspondência(s) encontrada(s) com alta confiança`;
    }
    
    // Populate table
    if (resultsBody) {
        resultsBody.innerHTML = '';
        
        results.forEach((result, index) => {
            const row = document.createElement('tr');
            row.className = 'border-b border-gray-300 hover:bg-gray-50';
            
            const { query, matched_items } = result;
            const bestScore = matched_items.length > 0 ? matched_items[0].score : 0;
            const bestValue = matched_items.length > 0 ? matched_items[0].value : 0;
            
            // Format matched items
            const matchedItemsHTML = matched_items.slice(0, 3).map(item => {
                return `<div class="mb-1">
                    <span class="font-medium text-gray-700">${escapeHtml(item.description)}</span>
                    <span class="text-xs text-gray-500 ml-2">(score: ${item.score.toFixed(3)}, R$ ${item.value.toFixed(2)})</span>
                </div>`;
            }).join('');
            
            const moreItems = matched_items.length > 3 ? 
                `<div class="text-xs text-gray-400">+${matched_items.length - 3} mais...</div>` : '';
            
            row.innerHTML = `
                <td class="py-3 px-4 text-sm text-gray-600 border-r border-gray-200">${index + 1}</td>
                <td class="py-3 px-4 text-sm text-gray-800 border-r border-gray-200">${escapeHtml(query)}</td>
                <td class="py-3 px-4 text-sm border-r border-gray-200">
                    ${matchedItemsHTML}
                    ${moreItems}
                </td>
                <td class="py-3 px-4 text-sm text-center border-r border-gray-200">
                    <span class="inline-block px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                        ${bestScore.toFixed(3)}
                    </span>
                </td>
                <td class="py-3 px-4 text-sm text-center">
                    <span class="inline-block px-2 py-1 bg-blue-50 text-blue-800 rounded text-xs font-medium">
                        R$ ${bestValue.toFixed(2)}
                    </span>
                </td>
            `;
            
            resultsBody.appendChild(row);
        });
    }
    
    // Setup download button
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.onclick = downloadCSV;
    }
}

// Show error message
function showError(message) {
    const progressSection = document.getElementById('progressSection');
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    
    if (progressSection) {
        progressSection.classList.add('hidden');
    }
    if (errorSection) {
        errorSection.classList.remove('hidden');
    }
    if (errorMessage) {
        errorMessage.textContent = message;
    }
}

// Download results as CSV
function downloadCSV() {
    if (!resultsData || resultsData.length === 0) {
        alert('Nenhum resultado para baixar');
        return;
    }
    
    // Build CSV content
    let csv = 'Consulta,Correspondência,Score,Distance,Valor\n';
    
    resultsData.forEach(result => {
        const { query, matched_items } = result;
        matched_items.forEach(item => {
            const row = [
                `"${query.replace(/"/g, '""')}"`,
                `"${item.description.replace(/"/g, '""')}"`,
                item.score.toFixed(4),
                item.distance.toFixed(4),
                item.value.toFixed(2)
            ].join(',');
            csv += row + '\n';
        });
    });
    
    // Create download link
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `resultados_${new Date().getTime()}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
