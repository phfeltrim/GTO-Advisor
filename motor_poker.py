import random
import collections
import sqlite3
import json
import joblib
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
import itertools

# --- CONFIGURAÇÕES ---
DB_FILE = 'poker_analytics.db'
MODEL_FILE = 'equity_model.pkl'
SCALER_FILE = 'scaler.pkl'

try:
    import seven_eval
except ImportError:
    seven_eval = None

MODELO_IA = None
SCALER_IA = None
try:
    MODELO_IA = joblib.load(MODEL_FILE)
    SCALER_IA = joblib.load(SCALER_FILE)
except Exception:
    pass

# --- RANGES PADRÃO ---
RANGES_DEF = {
    'Nit': {'pairs': range(9,15), 'suited': ['AK','AQ','AJ','AT','KQ'], 'offsuit': ['AK','AQ']},
    'Tight': {'pairs': range(7,15), 'suited': ['AK','AQ','AJ','AT','KQ','KJ','QJ','J10'], 'offsuit': ['AK','AQ','AJ','KQ']},
    'Standard': {'pairs': range(2,15), 'suited': ['AK','AQ','AJ','AT','A9','A8','KQ','KJ','KT','QJ','QT','JT','T9','98','87'], 'offsuit': ['AK','AQ','AJ','AT','KQ','KJ','QJ']},
    'Loose': 'ANY'
}
HAND_STRENGTH_MAP = {1:"Straight Flush",2:"Quadra",3:"Full House",4:"Flush",5:"Sequência",6:"Trinca",7:"Dois Pares",8:"Um Par",9:"Carta Alta"}

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('CREATE TABLE IF NOT EXISTS hands (state_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS training_logs (id INTEGER PRIMARY KEY, user_choice TEXT, correct_action TEXT, is_correct INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS bankroll (id INTEGER PRIMARY KEY, amount REAL, type TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS villains (name TEXT PRIMARY KEY, profile TEXT, notes TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS saved_ranges (name TEXT PRIMARY KEY, hands_json TEXT)')
    conn.commit(); conn.close()

def save_custom_range_db(name, hands_list):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT OR REPLACE INTO saved_ranges (name, hands_json) VALUES (?, ?)", (name, json.dumps(hands_list)))
        conn.commit(); conn.close()
        return True
    except: return False

def get_all_custom_ranges():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.execute("SELECT name, hands_json FROM saved_ranges")
        r = {row[0]: json.loads(row[1]) for row in cur.fetchall()}
        conn.close()
        return r
    except: return {}

def save_villain_profile(name, profile):
    if not name: return
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.execute("SELECT name FROM villains WHERE name=?", (name,))
        if cur.fetchone(): conn.execute("UPDATE villains SET profile=? WHERE name=?", (profile, name))
        else: conn.execute("INSERT INTO villains (name, profile) VALUES (?, ?)", (name, profile))
        conn.commit(); conn.close()
    except: pass

def get_villain_profile(name):
    if not name: return None
    try:
        conn = sqlite3.connect(DB_FILE)
        r = conn.execute("SELECT profile FROM villains WHERE name=?", (name,)).fetchone()
        conn.close()
        return r[0] if r else None
    except: return None

def update_bankroll(amount, type_str):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute('INSERT INTO bankroll (amount, type) VALUES (?, ?)', (amount, type_str))
        conn.commit(); conn.close()
    except: pass

def get_bankroll_history():
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute('SELECT amount, type FROM bankroll ORDER BY id ASC').fetchall()
        conn.close()
        bal=0; hist=[]
        for a,t in rows:
            if t=="WIN": bal+=a
            elif t=="LOSS": bal-=a
            hist.append(bal)
        return hist
    except: return []

def _auto_save_analysis(d):
    try: sqlite3.connect(DB_FILE).execute('INSERT INTO hands (state_json) VALUES (?)', (json.dumps(d),)).commit()
    except: pass

def log_training_result(u, c, i):
    try: sqlite3.connect(DB_FILE).execute('INSERT INTO training_logs (user_choice, correct_action, is_correct) VALUES (?,?,?)', (u,c,i)).commit()
    except: pass

def get_training_stats():
    try:
        c = sqlite3.connect(DB_FILE).cursor()
        c.execute("SELECT COUNT(*), SUM(is_correct) FROM training_logs")
        t, corr = c.fetchone()
        c.execute("SELECT is_correct FROM training_logs ORDER BY id DESC LIMIT 20")
        return {"total": t or 0, "accuracy": (corr/(t or 1))*100, "recent": [r[0] for r in c.fetchall()][::-1]}
    except: return {"total":0, "accuracy":0, "recent":[]}

# --- CLASSES ---
class Carta:
    VALORES={'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    NAIPES={'s':'♠','h':'♥','d':'♦','c':'♣'}; SUIT_INT={'s':0,'h':1,'d':2,'c':3}
    def __init__(self, v, n): 
        self.valor=self.VALORES.get(v.upper(),0); self.naipe_str=n.lower(); self.valor_str=v.upper()
        self.naipe_unicode = {'s':'♠','h':'♥','d':'♦','c':'♣'}.get(self.naipe_str,'?')
    def to_int(self): return (self.valor<<8)|self.SUIT_INT.get(self.naipe_str,0)
    def __repr__(self): return f"{self.valor_str}{self.naipe_unicode}"
    def __hash__(self): return hash((self.valor, self.naipe_str))
    def __eq__(self, o): return self.valor==o.valor and self.naipe_str==o.naipe_str

class Baralho:
    def __init__(self): self.cartas=[Carta(v,n) for v in Carta.VALORES for n in Carta.NAIPES]; self.shuffle()
    def shuffle(self): random.shuffle(self.cartas)
    def remover_cartas_conhecidas(self, k): ks={str(c) for c in k}; self.cartas=[c for c in self.cartas if str(c) not in ks]
    def deal(self, n=1): return [self.cartas.pop() for _ in range(n)] if len(self.cartas)>=n else []

# --- LÓGICA ---
def formatar_mao_preflop(c1, c2):
    v1,v2 = sorted([c1.valor, c2.valor], reverse=True)
    s = 's' if c1.naipe_str==c2.naipe_str else 'o'
    m = {v:k for k,v in Carta.VALORES.items()}
    return f"{m[v1]}{m[v2]}{s if v1!=v2 else ''}"

def expandir_range(lista, mortas):
    m={str(c) for c in mortas}; combos=[]
    for s in lista:
        if len(s)==2: # Pair
            r=s[0]
            for n1,n2 in itertools.combinations('shdc',2):
                c1,c2=Carta(r,n1),Carta(r,n2)
                if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
        elif 's' in s: # Suited
            r1,r2=s[0],s[1]
            for n in 'shdc':
                c1,c2=Carta(r1,n),Carta(r2,n)
                if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
        elif 'o' in s: # Off
            r1,r2=s[0],s[1]
            for n1 in 'shdc':
                for n2 in 'shdc':
                    if n1==n2: continue
                    c1,c2=Carta(r1,n1),Carta(r2,n2)
                    if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
    return combos

def gerar_combos(perfil, mortas):
    cust = get_all_custom_ranges()
    if isinstance(perfil, str) and perfil in cust: return expandir_range(cust[perfil], mortas)
    if 'Loose' in str(perfil): return None
    defin = RANGES_DEF.get(perfil.split()[0], {})
    if not defin: return None
    
    m={str(c) for c in mortas}; combos=[]
    for r in defin.get('pairs',[]):
        rc = [k for k,v in Carta.VALORES.items() if v==r][0]
        for n1,n2 in itertools.combinations('shdc',2):
            c1,c2=Carta(rc,n1),Carta(rc,n2)
            if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
    for tipo, is_s in [('suited',True), ('offsuit',False)]:
        for h in defin.get(tipo,[]):
            r1,r2=h[0],h[1]
            if is_s:
                for n in 'shdc':
                    c1,c2=Carta(r1,n),Carta(r2,n)
                    if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
            else:
                for n1 in 'shdc':
                    for n2 in 'shdc':
                        if n1==n2: continue
                        c1,c2=Carta(r1,n1),Carta(r2,n2)
                        if str(c1) not in m and str(c2) not in m: combos.append([c1,c2])
    return combos 

def avaliar(cartas):
    if not seven_eval or len(cartas)<5: return 0, "Aguardando..."
    r = seven_eval.find_hand([c.to_int() for c in cartas])
    return r, HAND_STRENGTH_MAP.get(r, "High Card")

# --- FUNÇÃO RECUPERADA ---
def analisar_perigo_board(board):
    """Calcula o perigo do board (0.0 a 1.0)."""
    if not board or len(board) < 3: return 0.0
    score = 0.0
    naipes = [c.naipe_str for c in board]
    vals = sorted([c.valor for c in board])
    
    # Flush danger
    if collections.Counter(naipes).most_common(1)[0][1] >= 3: score += 0.4
    
    # Straight danger
    if len(set(vals)) >= 3 and (max(vals) - min(vals) <= 4): score += 0.3
    
    # Paired board
    if len(vals) != len(set(vals)): score += 0.1
    
    return min(score, 1.0)
# --------------------------

def calc_equity(hero, board, opps, profile):
    deck = Baralho(); deck.remover_cartas_conhecidas(hero+board)
    combos = gerar_combos(profile, hero+board)
    
    # OTIMIZAÇÃO: Reduzimos de 1200/800 para 400/250
    # Isso triplica a velocidade sem perder muita precisão estratégica
    wins=0; its=400 if not combos else 250 
    
    # Cache local para evitar lookups repetidos
    deck_cartas = deck.cartas
    
    for _ in range(its):
        curr = list(deck_cartas); random.shuffle(curr)
        op_hands = []
        
        if combos: op_hands.append(random.choice(combos))
        elif len(curr)>=2: op_hands.append([curr.pop(), curr.pop()])
        
        for _ in range(opps-1):
            if len(curr)>=2: op_hands.append([curr.pop(), curr.pop()])
            
        sim = list(board)
        # Lógica de preenchimento do board simplificada
        while len(sim)<5 and curr:
            c=curr.pop()
            # Checagem de colisão simplificada
            conflict = False
            for h in op_hands:
                if c in h: 
                    conflict = True; break
            if not conflict: sim.append(c)
            
        hr,_ = avaliar(hero+sim); best=99
        for op in op_hands:
            vr,_ = avaliar(op+sim)
            if vr<best: best=vr
            
        if hr<best: wins+=1
        elif hr==best: wins+=0.5
        
    return (wins/its)*100

def calc_outs(hero, board):
    if len(board) in [0,5]: return [],0
    deck = Baralho(); deck.remover_cartas_conhecidas(hero+board)
    cr, _ = avaliar(hero+board); outs=set(); projs=[]
    suits = [c.naipe_str for c in hero+board]
    if any(q==4 for q in collections.Counter(suits).values()): projs.append("Flush Draw")
    for c in deck.cartas:
        nr, _ = avaliar(hero+board+[c])
        if (cr>4 and nr<=4) or (cr>5 and nr==5) or (cr>6 and nr==6):
            outs.add(str(c))
            if nr==5 and "Sequência" not in str(projs): projs.append("Sequência Draw")
    return projs, len(outs)

def get_gto_advice(equity, odds, board):
    danger = analisar_perigo_board(board) # Agora funciona!
    advice = {"action":"FOLD", "sizing":"N/A", "reason":f"EV - ({equity:.1f}% vs {odds:.1f}%)"}
    if equity >= 75: advice={"action":"BET/RAISE","sizing":"75%+","reason":"Valor Absoluto"}
    elif 60<=equity<75: advice={"action":"CHECK/CALL","sizing":"Control","reason":"Bluff Catcher"}
    elif 30<=equity<60:
        if danger>0.4 and (equity-odds)>-10: advice={"action":"RAISE (SEMI)","sizing":"50%","reason":"Semi-Blefe"}
        elif equity>=odds: advice={"action":"CALL","sizing":"N/A","reason":"Odds Favoráveis"}
    else:
        if equity>=odds: advice={"action":"CALL","sizing":"N/A","reason":"Odds Matemáticas"}
    return advice

def get_preflop_advice(hand, scenario):
    h_str = formatar_mao_preflop(hand[0], hand[1])
    t1={'AA','KK','QQ','AKs'}; t2={'JJ','TT','AQs','AKo','AJs'}
    t3={'99','88','77','KQs','ATs','AQo','KJs','QJs','JTs'}
    t4={'66','55','44','33','22','Axs','KQo'}
    if "Livre" in scenario:
        if h_str in t1 or h_str in t2: return {"action":"RAISE","sizing":"3x","reason":"Premium"}
        if h_str in t3: return {"action":"RAISE","sizing":"2.5x","reason":"Padrão"}
        if h_str in t4: return {"action":"RAISE","sizing":"2.2x","reason":"Roubo"}
    elif "Raise" in scenario:
        if h_str in t1: return {"action":"3-BET","sizing":"3x","reason":"Valor"}
        if h_str in t2 or h_str in t3: return {"action":"CALL","sizing":"Flat","reason":"Defesa"}
    elif "3-Bet" in scenario:
        if h_str in t1: return {"action":"4-BET","sizing":"Shove","reason":"Nut"}
        if h_str in ['JJ','TT','AKo']: return {"action":"CALL","sizing":"Flat","reason":"SetMine"}
    return {"action":"FOLD","sizing":"N/A","reason":"Fraco"}

def analisar_situacao(hero_str, board_str, pot, call, stack, opps, profile, pre_scen, v_name=None):
    try: h=[Carta(s[:-1],s[-1]) for s in hero_str]; b=[Carta(s[:-1],s[-1]) for s in board_str]
    except: return {"erro":"Erro Cartas"}
    if v_name and profile: save_villain_profile(v_name, profile)
    
    pot_f=pot+call; odds=(call/pot_f*100) if pot_f>0 else 0
    spr=stack/pot_f if pot_f>0 else 0
    spr_msg = " [Comitado]" if spr<3 else ""
    
    if not b:
        adv=get_preflop_advice(h, pre_scen); eq=calc_equity(h,[],opps,profile)
        draws="-"; n_outs=0; _,name=avaliar(h)
    else:
        eq=calc_equity(h,b,opps,profile)
        adv=get_gto_advice(eq, odds, b)
        if spr<3 and eq>45 and "FOLD" in adv['action']: adv['action']="SHOVEL"; adv['reason']+=" (SPR)"
        
        projs, n_outs = calc_outs(h,b)
        draws=", ".join(projs) if projs else "Nenhum"; _,name=avaliar(h+b)
        
    res={
        "hand_strength":name, "equity":round(eq,1), "pot_odds_pct":round(odds,1),
        "recommendation":adv["action"], "sizing":adv["sizing"], 
        "reasoning":f"{adv['reason']}{spr_msg}", "draws":draws, "num_outs":n_outs, "spr_val":round(spr,1)
    }
    _auto_save_analysis(res)
    return res