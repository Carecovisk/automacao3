
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
    const bestTable = doc.querySelector('html body div#pagina table tbody tr td table tbody tr td table tbody tr td table tbody tr td div#conteudo fieldset strong form table:nth-of-type(2)');
    const maxRows = bestTable ? bestTable?.rows?.length : 0;
    statusDiv.textContent = `Sucesso! Extraída a tabela com ${maxRows} linhas.`;

    // 5. Converte a "Melhor Tabela" usando SheetJS
    const workbook = XLSX.utils.table_to_book(bestTable, { raw: true });
    const worksheet = workbook.Sheets[workbook.SheetNames[0]];

    // 6. Converte a planilha para JSON e exibe
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }); // header:1 traz array de arrays
    document.getElementById('output').textContent = JSON.stringify(jsonData, null, 2);

});
