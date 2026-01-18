import pandas as pd

def get_product_descriptions(pesquisa_path : str) -> pd.DataFrame:

    df_pesquisa = pd.read_excel(pesquisa_path, skiprows=16, sheet_name='Planilha1')

    if 'DESCRIÇÃO' not in df_pesquisa.columns:
        raise KeyError("Coluna 'DESCRIÇÃO' não encontrada no DataFrame.")

    return df_pesquisa[['DESCRIÇÃO']].dropna().drop_duplicates().reset_index(drop=True)

def filter_and_calculate_mean_loja(file_path : str, description_filter=None, sheet_name=None) -> pd.DataFrame:
    """
    Filter rows containing 'PNEU' and calculate weighted average prices.
    
    Args:
        df: DataFrame with columns 'descr_compl', 'vl_item', and 'qtd'
    
    Returns:
        DataFrame with product descriptions, quantities, and average unit prices
    """

    df = pd.read_excel(file_path, skiprows=4, sheet_name=sheet_name)
    
    # 2. Filtrar as linhas onde 'descr_compl' contém a palavra "PNEU"
    df_pneu = df[df['descr_compl'].str.contains(description_filter, case=False, na=False)].copy()

    # 3. Criar o dataframe com as médias dos valores de cada produto
    df_medias = df_pneu.groupby('descr_compl').agg({
        'vl_item': 'sum',
        'qtd': 'sum'
    }).reset_index()

    # Criar a coluna de média unitária
    df_medias['media'] = df_medias['vl_item'] / df_medias['qtd']
    df_medias.drop(columns=['vl_item'], inplace=True)
    
    return df_medias

if __name__ == "__main__":
    # Exemplo de uso
    df_loja = get_product_descriptions('./data/pesquisa.xlsx')
    print(df_loja.head())
