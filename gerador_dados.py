# gerador_dados.py
# PokerData Strategist - Geração de Dados com Engenharia de Features (Smart Features)

import csv
import random
import collections
import numpy as np
from motor_poker import Baralho, Carta, avaliar_mao_bruta, analisar_perigo_board

# --- CONFIGURAÇÕES ---
NUM_MAOS_PARA_GERAR = 50000  # 50k mãos bem feitas valem mais que 1kk aleatórias
SIMULACOES_MONTE_CARLO = 600 # Rápido, apenas para obter o "Label" (Target)
ARQUIVO_SAIDA = 'poker_smart_dataset.csv'

def calcular_equity_rapida(hero_hand, board, num_opponents, sims=500):
    """
    Versão simplificada do Monte Carlo para gerar o 'Gabarito' (Target) do dataset.
    """
    deck = Baralho()
    # Remove cartas já usadas
    used = set(hero_hand + board)
    deck.cartas = [c for c in deck.cartas if c not in used]
    
    wins = 0
    for _ in range(sims):
        curr_deck = list(deck.cartas)
        random.shuffle(curr_deck)
        
        # Distribui vilões
        villains = []
        for _ in range(num_opponents):
            villains.append([curr_deck.pop(), curr_deck.pop()])
            
        # Completa board se necessário
        needed = 5 - len(board)
        run_board = board + [curr_deck.pop() for _ in range(needed)]
        
        # Avalia
        # Nota: avaliar_mao_bruta retorna (rank_int, nome). Rank menor = melhor.
        h_rank, _ = avaliar_mao_bruta(hero_hand + run_board)
        
        best_v = 99
        for v_hand in villains:
            v_rank, _ = avaliar_mao_bruta(v_hand + run_board)
            if v_rank < best_v: best_v = v_rank
            
        if h_rank < best_v: wins += 1
        elif h_rank == best_v: wins += 0.5 # Empate
        
    return (wins / sims) * 100

def extrair_features_inteligentes(hero_hand, board, num_opponents):
    """
    O SEGREDO DO SUCESSO:
    Converte cartas em CONCEITOS. A IA aprende padrões, não cartas específicas.
    """
    features = []
    
    # 1. Força Atual da Mão (0 a 1, onde 1 é Nut Absoluto)
    # seven_eval retorna 1 (SF) a 9 (High Card). Vamos inverter e normalizar.
    raw_rank, _ = avaliar_mao_bruta(hero_hand + board)
    # Transformação: 1->1.0 (Bom), 9->0.0 (Ruim)
    strength_norm = (10 - raw_rank) / 9.0 
    features.append(strength_norm)
    
    # 2. Perigo do Board (Texture)
    # Reutiliza a lógica do motor_poker (0.0 a 1.0)
    danger = analisar_perigo_board(board)
    features.append(danger)
    
    # 3. Potencial de Flush (Heroi)
    hero_suits = [c.naipe_str for c in hero_hand]
    board_suits = [c.naipe_str for c in board]
    all_suits = hero_suits + board_suits
    counts = collections.Counter(all_suits)
    # Temos um flush draw? (4 cartas do mesmo naipe)
    max_suit = counts.most_common(1)[0][1] if counts else 0
    features.append(1 if max_suit == 4 else 0) # Flush Draw
    features.append(1 if max_suit >= 5 else 0) # Flush Feito
    
    # 4. Potencial de Sequência (Heroi)
    # Simplificado: Checa se temos 4 cartas conectadas
    all_vals = sorted(list(set([c.valor for c in hero_hand + board])))
    gaps = 0
    connected_4 = 0
    if len(all_vals) >= 4:
        for i in range(len(all_vals)-3):
            window = all_vals[i:i+4]
            if window[-1] - window[0] == 3: # 4 cartas seguidas (ex: 5,6,7,8)
                connected_4 = 1
                break
    features.append(connected_4)
    
    # 5. High Cards (Temos cartas altas na mão?)
    hero_vals = [c.valor for c in hero_hand]
    features.append(1 if max(hero_vals) >= 12 else 0) # Tem Q, K ou A?
    
    # 6. Par na Mão (Pocket Pair)
    features.append(1 if hero_vals[0] == hero_vals[1] else 0)
    
    # 7. Número de Oponentes (Contexto)
    features.append(num_opponents)
    
    # 8. Street (Progresso do jogo: 0=Pre, 0.33=Flop, 0.66=Turn, 1=River)
    street_val = 0
    if len(board) == 3: street_val = 0.33
    elif len(board) == 4: street_val = 0.66
    elif len(board) == 5: street_val = 1.0
    features.append(street_val)

    return features

def gerar_dataset():
    print(f"--- INICIANDO GERAÇÃO DE DADOS ({NUM_MAOS_PARA_GERAR} Mãos) ---")
    print("Usando Features Abstratas (Melhor generalização para IA)...")
    
    # Nomes das colunas para o CSV
    colunas = [
        'strength_curr', 'board_danger', 'is_fd', 'is_flush', 
        'is_straight', 'has_high_card', 'is_pocket_pair', 
        'num_opponents', 'street_progress', 
        'target_equity' # O Rótulo (Target)
    ]
    
    with open(ARQUIVO_SAIDA, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(colunas)
        
        for i in range(NUM_MAOS_PARA_GERAR):
            try:
                deck = Baralho()
                num_opp = random.randint(1, 5)
                
                # Heroi
                hero = deck.deal(2)
                
                # Street aleatória (focando mais em pós-flop onde a IA precisa de ajuda)
                stage = random.choice(['flop', 'flop', 'turn', 'turn', 'river']) 
                board = []
                if stage == 'flop': board = deck.deal(3)
                elif stage == 'turn': board = deck.deal(4)
                elif stage == 'river': board = deck.deal(5)
                
                # 1. Calcular Equity Real (O "Gabarito")
                equity_real = calcular_equity_rapida(hero, board, num_opp, SIMULACOES_MONTE_CARLO)
                
                # 2. Extrair Features Inteligentes (O que a IA vai ver)
                feats = extrair_features_inteligentes(hero, board, num_opp)
                
                # Salvar
                row = feats + [round(equity_real, 2)]
                writer.writerow(row)
                
                if (i+1) % 1000 == 0:
                    print(f"Progresso: {i+1}/{NUM_MAOS_PARA_GERAR} mãos geradas.")
                    
            except Exception as e:
                print(f"Erro na iteração {i}: {e}")
                continue

    print(f"\nSucesso! Dataset salvo em '{ARQUIVO_SAIDA}'.")

if __name__ == "__main__":
    gerar_dataset()