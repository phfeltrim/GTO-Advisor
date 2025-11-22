# treinador_modelo.py
# PokerData Strategist - Treinamento de IA com Smart Features

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

# --- CONFIGURAÇÕES ---
NOME_ARQUIVO_DATASET = 'poker_smart_dataset.csv'
NOME_ARQUIVO_MODELO = 'equity_model.pkl'
NOME_ARQUIVO_SCALER = 'scaler.pkl'

def treinar_modelo():
    print("--- POKER AI TRAINER (Smart Features) ---")
    
    # 1. Carregar Dados
    print(f"Carregando dataset '{NOME_ARQUIVO_DATASET}'...")
    try:
        df = pd.read_csv(NOME_ARQUIVO_DATASET)
    except FileNotFoundError:
        print(f"ERRO CRÍTICO: '{NOME_ARQUIVO_DATASET}' não encontrado.")
        print("Execute 'gerador_dados.py' primeiro para criar a base de conhecimento.")
        return

    print(f"Dataset carregado: {len(df)} exemplos.")

    # 2. Separação Features (X) vs Target (y)
    # O gerador salvou o target como 'target_equity' (0 a 100)
    X = df.drop('target_equity', axis=1)
    
    # Normalizamos o target para 0.0 a 1.0 para ajudar a convergência da Rede Neural
    y = df['target_equity'] / 100.0 

    # Split de Treino/Teste (90% treino, 10% validação)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

    # 3. Scaling (Padronização)
    # Essencial para redes neurais. O Scaler aprende a média e desvio padrão do treino.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"Dados preparados. Features de entrada: {X.columns.tolist()}")

    # 4. Construção da Rede Neural
    # Reduzimos um pouco a arquitetura pois as features agora são mais densas e significativas.
    # (64, 32) é suficiente e muito rápido para inferência em tempo real.
    print("Configurando Rede Neural (MLP)...")
    model = MLPRegressor(
        hidden_layer_sizes=(64, 32), 
        activation='relu',
        solver='adam',
        max_iter=1000,          # Mais iterações permitidas
        learning_rate_init=0.001,
        early_stopping=True,    # Para se parar de aprender (evita Overfitting)
        validation_fraction=0.1,
        random_state=42,
        verbose=True            # Mostra o log de erro descendo
    )

    # 5. Treinamento
    print("\n>>> INICIANDO TREINAMENTO <<<")
    model.fit(X_train_scaled, y_train)
    print("Treinamento concluído.")

    # 6. Avaliação Profissional
    y_pred = model.predict(X_test_scaled)
    
    # Converter de volta para porcentagem (0-100) para leitura humana
    y_test_pct = y_test * 100
    y_pred_pct = y_pred * 100
    
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test_pct, y_pred_pct)

    print("\n--- RELATÓRIO DE PERFORMANCE ---")
    print(f"R² Score: {r2:.4f} (Ideal > 0.90)")
    print(f"Erro Médio Absoluto (MAE): {mae:.2f}%")
    print("-" * 30)
    print(f"Interpretação: Em média, a IA erra a equidade por {mae:.2f} pontos percentuais.")
    print("-" * 30)

    # 7. Salvar Artefatos
    print(f"Salvando modelo em '{NOME_ARQUIVO_MODELO}'...")
    joblib.dump(model, NOME_ARQUIVO_MODELO)
    
    print(f"Salvando scaler em '{NOME_ARQUIVO_SCALER}'...")
    joblib.dump(scaler, NOME_ARQUIVO_SCALER)
    
    print("\nPROCESSO FINALIZADO COM SUCESSO.")
    print("Agora sua IA aprendeu a LER o jogo, não apenas decorar cartas.")

if __name__ == '__main__':
    treinar_modelo()