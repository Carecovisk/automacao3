// Tasks page - lists all tasks and polls for live status updates

let pollingInterval = null;

const STATUS_MAP = {
    pending: 'Aguardando',
    running: 'Processando',
    completed: 'Concluído',
    failed: 'Falhou',
};

const STATUS_COLORS = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
};

document.addEventListener('DOMContentLoaded', () => {
    fetchAndRender();
    pollingInterval = setInterval(checkAndPoll, 2000);
});

async function fetchAndRender() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const tasks = await response.json();
        renderTasks(tasks);

        // Stop polling when all tasks are in a terminal state
        const allDone = tasks.length > 0 && tasks.every(t => t.status === 'completed' || t.status === 'failed');
        if (allDone) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    } catch (err) {
        console.error('Erro ao buscar tarefas:', err);
    }
}

function checkAndPoll() {
    fetchAndRender();
}

function renderTasks(tasks) {
    const emptyState = document.getElementById('emptyState');
    const tasksContainer = document.getElementById('tasksContainer');
    const tasksBody = document.getElementById('tasksBody');

    if (!tasks || tasks.length === 0) {
        emptyState.classList.remove('hidden');
        tasksContainer.classList.add('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    tasksContainer.classList.remove('hidden');

    tasksBody.innerHTML = '';
    tasks.forEach(task => {
        const { task_id, file_name, status, progress, total, percentage } = task;
        const statusLabel = STATUS_MAP[status] || status;
        const statusColor = STATUS_COLORS[status] || 'bg-gray-100 text-gray-700';
        const pct = typeof percentage === 'number' ? percentage.toFixed(1) : '0.0';
        const progressLabel = `${progress ?? 0} / ${total ?? 0} (${pct}%)`;

        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-200 hover:bg-gray-50';
        tr.innerHTML = `
            <td class="py-3 px-4 text-sm text-gray-800 border-r border-gray-200 max-w-xs truncate" title="${escapeHtml(file_name)}">${escapeHtml(file_name)}</td>
            <td class="py-3 px-4 text-sm border-r border-gray-200">
                <span class="inline-block px-2 py-1 rounded-full text-xs font-medium ${statusColor}">${statusLabel}</span>
            </td>
            <td class="py-3 px-4 text-sm text-gray-600 border-r border-gray-200">
                <div class="flex items-center gap-2">
                    <div class="w-32 bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
                    </div>
                    <span class="text-xs text-gray-500">${progressLabel}</span>
                </div>
            </td>
            <td class="py-3 px-4 text-sm">
                <a href="/results-view?taskId=${encodeURIComponent(task_id)}"
                   class="py-1 px-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-xs font-medium">
                    Ver Resultados
                </a>
            </td>
        `;
        tasksBody.appendChild(tr);
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
