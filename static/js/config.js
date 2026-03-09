/* config.js – Handles loading and saving application settings */

const form = document.getElementById('config-form');
const useLlmCheckbox = document.getElementById('use_llm');
const llmFields = document.getElementById('llm-fields');
const geminiKeyInput = document.getElementById('gemini_api_key');
const abbrevCheckbox = document.getElementById('use_llm_abbreviation_expansion');
const thresholdInput = document.getElementById('high_confidence_threshold');
const toast = document.getElementById('toast');

/** Show/hide and enable/disable the LLM-dependent fields based on the master toggle. */
function applyLlmToggle(enabled) {
    llmFields.style.opacity = enabled ? '1' : '0.45';
    geminiKeyInput.disabled = !enabled;
    abbrevCheckbox.disabled = !enabled;
}

/** Display a temporary notification message. */
function showToast(message, isError = false) {
    toast.textContent = message;
    toast.className = [
        'mt-4 p-3 rounded-md text-center text-sm font-medium',
        isError ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700',
    ].join(' ');
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 4000);
}

/** Fetch current config from the API and populate the form. */
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        useLlmCheckbox.checked = !!data.use_llm;
        geminiKeyInput.value = data.gemini_api_key ?? '';
        abbrevCheckbox.checked = !!data.use_llm_abbreviation_expansion;
        thresholdInput.value = data.high_confidence_threshold ?? 0.9;

        applyLlmToggle(useLlmCheckbox.checked);
    } catch (err) {
        showToast('Erro ao carregar configurações: ' + err.message, true);
    }
}

/** React to the master LLM toggle change. */
useLlmCheckbox.addEventListener('change', () => {
    applyLlmToggle(useLlmCheckbox.checked);
});

/** Submit handler — POST current form values to /api/config. */
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
        use_llm: useLlmCheckbox.checked,
        gemini_api_key: geminiKeyInput.value,
        use_llm_abbreviation_expansion: abbrevCheckbox.checked,
        high_confidence_threshold: parseFloat(thresholdInput?.value.replace(',', '.')) || 0.9,
    };

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const body = await res.text();
            throw new Error(`HTTP ${res.status}: ${body}`);
        }
        showToast('Configurações salvas com sucesso!');
    } catch (err) {
        showToast('Erro ao salvar configurações: ' + err.message, true);
    }
});

// Initialise on page load
document.addEventListener('DOMContentLoaded', loadConfig);
