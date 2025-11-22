# ♠️ Hold'em GTO Advisor - Ultimate Edition

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Status](https://img.shields.io/badge/Status-Finished-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

O **Hold'em GTO Advisor** é uma ferramenta avançada de estratégia e treinamento para Texas Hold'em No-Limit. Diferente de calculadoras simples de equidade, este software combina Simulação de Monte Carlo, Lógica GTO (Game Theory Optimal) e gestão de Ranges para oferecer conselhos estratégicos em tempo real (EV+, Fold/Call/Raise).

Ele possui modos de **Jogo (Carreira)**, **Treinamento (Dojo)** e um **Editor de Ranges** completo.

---

## 🚀 Funcionalidades Principais

### 🧠 Motor Estratégico
* **Cálculo Híbrido:** Utiliza simulações de Monte Carlo otimizadas para calcular Equidade contra ranges específicos.
* **Análise de Outs:** Identifica automaticamente projetos (Flush Draw, Sequências, Gutshots) e conta os outs.
* **Lógica GTO:** Sugere ações baseadas em EV (Valor Esperado), Pot Odds e Textura do Board.
* **SPR & Momentum:** Ajusta a estratégia baseada no Stack-to-Pot Ratio e no momento da sessão (ganhando ou perdendo).

### 🎮 Modos de Uso
* **Modo Carreira (Manual):** Para jogar com amigos ou online (onde permitido). Calcula a jogada e registra seus ganhos/perdas em um banco de dados local (SQLite).
* **Modo Dojo (Treino):** Um "Quiz" infinito onde a IA gera cenários e você deve adivinhar a melhor jogada. Ótimo para treinar sem arriscar dinheiro.

### 🛠️ Ferramentas Avançadas
* **Editor de Ranges (13x13):** Crie e salve ranges personalizados (ex: "João UTG Tight") visualmente.
* **Profiler de Vilões:** Salva o perfil de oponentes pelo nome. O sistema lembra se o "Pedro" é *Loose* ou *Nit*.
* **Dashboard Analytics:** Gráficos com Matplotlib mostrando a evolução da sua banca e precisão no treino.

---

## 📸 Screenshots

*(Adicione aqui prints do seu software rodando, por exemplo:)*
*Tela Principal (Modo Carreira)*
*Editor de Ranges*
*Dashboard de Analytics*

---

## 🛠️ Tecnologias Utilizadas

O projeto foi desenvolvido 100% em **Python** com foco em modularidade e performance.

* **Interface Gráfica (GUI):** `tkinter` (Customizada com temas Dark Mode).
* **Processamento de Imagem:** `Pillow (PIL)` para renderização de cartas.
* **Análise de Dados:** `pandas` e `numpy`.
* **Visualização de Dados:** `matplotlib` (Gráficos integrados na GUI).
* **Banco de Dados:** `sqlite3` (Nativo) para persistência de mãos, banca e perfis.
* **Inteligência Artificial:** `scikit-learn` (Random Forest/MLP) e Algoritmos de Monte Carlo.

---

## 📦 Como Executar (Desenvolvedores)

Se você deseja rodar o código fonte ou modificar o projeto:

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/SEU_USUARIO/holdem-gto-advisor.git](https://github.com/SEU_USUARIO/holdem-gto-advisor.git)
    cd holdem-gto-advisor
    ```

2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Execute a aplicação:**
    ```bash
    python ui_advisor.py
    ```

---

## 📂 Estrutura do Projeto

```text
holdem-gto-advisor/
├── cards/              # Imagens das cartas (png)
├── ui_advisor.py       # Interface Gráfica (Frontend)
├── motor_poker.py      # Lógica, IA e Banco de Dados (Backend)
├── equity_model.pkl    # Modelo de ML treinado (Opcional)
├── scaler.pkl          # Normalizador de dados (Opcional)
├── requirements.txt    # Lista de bibliotecas
└── README.md           # Documentação