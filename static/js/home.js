
let currentData = null;
let currentDescription = null;

document.addEventListener('paste', function (e) {
    e.preventDefault();
    const statusDiv = document.getElementById('status');

    // 1. Pega o HTML sujo (pagina inteira)
    const clipboardHTML = e.clipboardData.getData('text/html');
    if (!clipboardHTML) {
        statusDiv.textContent = "Erro: Nenhum HTML encontrado. Você copiou do site da secretaria?";
        return;
    }

    statusDiv.textContent = "Processando dados...";

    // 2. Parser do HTML na memória
    const parser = new DOMParser();
    const doc = parser.parseFromString(clipboardHTML, "text/html");

    // 3. Encontra conteudo relevante
    const description = doc.querySelector('html body div#pagina table tbody tr td table tbody tr td table tbody tr td table tbody tr td div#conteudo fieldset strong form table tbody tr td').textContent.trim();
    console.log("Descrição encontrada:", description);
    
    // 4. Encontra a "Melhor Tabela" (a que tem mais linhas)
    const bestTable = doc.querySelector('html body div#pagina table tbody tr td table tbody tr td table tbody tr td table tbody tr td div#conteudo fieldset strong form table:nth-of-type(2)');
    const maxRows = bestTable ? bestTable?.rows?.length : 0;
    statusDiv.textContent = `Sucesso! Extraída a tabela com ${maxRows} linhas.`;

    // 5. Converte a "Melhor Tabela" usando SheetJS
    const workbook = XLSX.utils.table_to_book(bestTable, { raw: true });
    const worksheet = workbook.Sheets[workbook.SheetNames[0]];

    // 6. Converte a planilha para JSON e exibe
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }); // header:1 traz array de arrays
    document.getElementById('output').textContent = JSON.stringify(jsonData, null, 2);

    // 7. Store data and show confirm button
    currentData = jsonData;
    currentDescription = description;
    document.getElementById('confirmBtn').style.display = 'block';

});

// Handle confirm button click
document.getElementById('confirmBtn').addEventListener('click', async function() {
    if (!currentData || !currentDescription) {
        alert('Nenhum dado para confirmar');
        return;
    }

    try {
        const response = await fetch('/api/confirm-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                data: currentData,
                description: currentDescription
            })
        });

        if (response.ok) {
            alert('Dados enviados com sucesso!');
            console.log('Resposta do servidor:', await response.json());
        } else {
            alert('Erro ao enviar dados: ' + response.statusText);
        }
    } catch (error) {
        alert('Erro ao enviar dados: ' + error.message);
    }
});
