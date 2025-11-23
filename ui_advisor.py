import requests
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from PIL import Image, ImageTk
import os, sys, random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from motor_poker import (
    init_db, analisar_situacao, Baralho, log_training_result, 
    get_training_stats, update_bankroll, get_bankroll_history,
    save_custom_range_db, get_all_custom_ranges, get_villain_profile
)

# --- CONFIGURAÇÃO DA API (No futuro será seu site real) ---
API_URL = "https://gto-server-api.onrender.com"

# --- CONFIG ---
def resource_path(relative_path):
    try: base = sys._MEIPASS
    except: base = os.path.abspath(".")
    return os.path.join(base, relative_path)

CARDS_DIR = resource_path("cards")
CARD_SIZE_SLOT = (50, 70); CARD_SIZE_GRID = (40, 60)
NAIPES = ['c', 'd', 'h', 's']; VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
RANKS_ORDER = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

# --- CACHE GLOBAL DE IMAGENS ---
# Carregaremos as imagens apenas uma vez para evitar lentidão no disco
IMG_CACHE_SLOT = {} # Para a mesa principal
IMG_CACHE_GRID = {} # Para o popup

def pre_load_images():
    """Carrega todas as 52 cartas na RAM na inicialização."""
    for n in NAIPES:
        for v in VALORES:
            code = f"{v}{n}"
            try:
                path = os.path.join(CARDS_DIR, f"{code}.png")
                pil_img = Image.open(path)
                # Cache Slot (Grande)
                IMG_CACHE_SLOT[code] = ImageTk.PhotoImage(pil_img.resize(CARD_SIZE_SLOT, Image.LANCZOS))
                # Cache Grid (Pequeno)
                IMG_CACHE_GRID[code] = ImageTk.PhotoImage(pil_img.resize(CARD_SIZE_GRID, Image.LANCZOS))
            except: pass

# --- JANELAS ---
class RangeEditorWindow(Toplevel):
    def __init__(self, parent, on_save_callback):
        super().__init__(parent); self.title("Editor de Ranges"); self.geometry("900x750"); self.configure(bg="#1e1e1e")
        self.on_save_callback = on_save_callback; self.selected_hands = set(); self.buttons = {}; self._setup_ui()

    def _setup_ui(self):
        top = tk.Frame(self, bg="#1e1e1e"); top.pack(fill=tk.X, pady=10)
        tk.Button(top, text="< Voltar", bg="#333", fg="white", command=self.destroy).pack(side=tk.LEFT, padx=10)
        tk.Label(top, text="Nome:", bg="#1e1e1e", fg="white").pack(side=tk.LEFT)
        self.entry_name = tk.Entry(top, bg="#333", fg="white"); self.entry_name.pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="SALVAR", bg="#007acc", fg="white", command=self._save).pack(side=tk.LEFT, padx=20)
        tk.Label(top, text="Verde=Par | Azul=Suited | Laranja=Off", bg="#1e1e1e", fg="#aaa").pack(side=tk.RIGHT, padx=10)

        gf = tk.Frame(self, bg="#1e1e1e"); gf.pack(pady=10, expand=True)
        for r, r1 in enumerate(RANKS_ORDER):
            for c, r2 in enumerate(RANKS_ORDER):
                h=""; col=""
                if r==c: h=f"{r1}{r2}"; col="#2e7d32"
                elif r<c: h=f"{r1}{r2}s"; col="#0277bd"
                else: h=f"{r2}{r1}o"; col="#ef6c00"
                b=tk.Button(gf, text=h, width=4, height=1, font=("Segoe UI",9), bg="#333", fg="white", command=lambda x=h: self._t(x))
                b.grid(row=r, column=c, padx=1, pady=1)
                self.buttons[h]={'b':b, 'c':col, 'a':False}

    def _t(self, h):
        s=self.buttons[h]; s['a']=not s['a']
        if s['a']: s['b'].config(bg=s['c'], fg="white", font=("Segoe UI",9,"bold")); self.selected_hands.add(h)
        else: s['b'].config(bg="#333", fg="white", font=("Segoe UI",9,"normal")); self.selected_hands.discard(h)

    def _save(self):
        n=self.entry_name.get().strip()
        if not n or not self.selected_hands: return messagebox.showerror("Erro", "Dados inválidos.")
        if save_custom_range_db(n, list(self.selected_hands)):
            messagebox.showinfo("Sucesso", "Salvo!"); self.on_save_callback(); self.destroy()
        else: messagebox.showerror("Erro", "Erro no banco.")

class CardSelectorPopup(Toplevel):
    def __init__(self, parent, callback, cartas_bloqueadas):
        super().__init__(parent); self.title("Selecione"); self.geometry("600x350"); self.configure(bg="#2d2d2d")
        self.callback = callback; self.cartas_bloqueadas = cartas_bloqueadas; self._criar_grid()
    def _criar_grid(self):
        for r, n in enumerate(NAIPES):
            for c, v in enumerate(VALORES):
                code = f"{v}{n}"; is_blk = code in self.cartas_bloqueadas
                st = "disabled" if is_blk else "normal"; bg = "#111" if is_blk else "#2d2d2d"
                
                # USA O CACHE AQUI
                if code in IMG_CACHE_GRID:
                    btn = tk.Button(self, image=IMG_CACHE_GRID[code], bg=bg, state=st, bd=0, command=lambda x=code: self._sel(x))
                else:
                    btn = tk.Button(self, text=code, width=4, state=st, bg=bg, command=lambda x=code: self._sel(x))
                btn.grid(row=r, column=c, padx=2, pady=2)
        tk.Button(self, text="LIMPAR", bg="#d32f2f", fg="white", command=lambda: self._sel(None)).grid(row=4, column=0, columnspan=13, sticky="ew")
    def _sel(self, c): self.callback(c); self.destroy()

class PokerAdvisorApp:
    def __init__(self, root):
        self.root = root; self.root.title("Hold'em GTO Advisor - Ultimate Turbo"); self.root.geometry("1050x850"); self.root.configure(bg="#1e1e1e")
        
        # Carrega imagens na RAM
        pre_load_images()
        
        init_db(); self._setup_styles()
        self.selected_cards=[None]*7; self.slot_buttons=[]; self.current_train_solution = None 
        self._mostrar_menu_principal()

    def _setup_styles(self):
        s = ttk.Style(); s.theme_use('clam')
        s.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        s.configure("Green.Horizontal.TProgressbar", troughcolor="#333", background="#50fa7b")
        s.configure("Red.Horizontal.TProgressbar", troughcolor="#333", background="#ff5555")
        s.configure("Yellow.Horizontal.TProgressbar", troughcolor="#333", background="#f1fa8c")

    def _limpar_tela(self):
        for w in self.root.winfo_children(): w.destroy()

    def _mostrar_menu_principal(self):
        self._limpar_tela(); f = tk.Frame(self.root, bg="#1e1e1e"); f.pack(expand=True)
        tk.Label(f, text="♠️ POKER STRATEGIST ♦️", font=("Segoe UI", 26, "bold"), bg="#1e1e1e", fg="#007acc").pack(pady=20)
        h = get_bankroll_history(); b = h[-1] if h else 0; col = "#50fa7b" if b>=0 else "#ff5555"
        tk.Label(f, text=f"BANCA: ${b:.2f}", font=("Consolas", 16), bg="#252526", fg=col, padx=20).pack(pady=(0,30))
        
        b_cfg = {"font":("Segoe UI", 14), "width":30, "pady":5}
        tk.Button(f, text="JOGAR (CARREIRA)", bg="#2e7d32", fg="white", command=self._iniciar_jogo, **b_cfg).pack()
        tk.Button(f, text="EDITOR DE RANGES", bg="#ff9800", fg="white", command=self._abrir_editor, **b_cfg).pack()
        tk.Button(f, text="DOJO (TREINO)", bg="#7b1fa2", fg="white", command=self._iniciar_treino, **b_cfg).pack()
        tk.Button(f, text="ANALYTICS", bg="#0288d1", fg="white", command=self._mostrar_dash, **b_cfg).pack()

    def _abrir_editor(self): RangeEditorWindow(self.root, lambda: None)

    def _construir_ui(self, treino=False):
        self._limpar_tela(); self.treino = treino; self.selected_cards=[None]*7; self.slot_buttons=[]
        m = tk.Frame(self.root, bg="#1e1e1e"); m.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        top = tk.Frame(m, bg="#1e1e1e"); top.pack(fill=tk.X)
        tk.Button(top, text="< Menu", bg="#333", fg="white", command=self._mostrar_menu_principal).pack(side=tk.LEFT)
        t, c = ("DOJO", "#e040fb") if treino else ("CARREIRA", "#4caf50")
        tk.Label(top, text=t, font=("Segoe UI", 18, "bold"), bg="#1e1e1e", fg=c).pack(side=tk.LEFT, padx=20)

        cf = tk.LabelFrame(m, text=" Mesa ", bg="#252526", fg="white"); cf.pack(fill=tk.X, pady=10)
        self._criar_slots(cf)
        if not treino: tk.Button(cf, text="LIMPAR", bg="#d32f2f", fg="white", command=self._limpar_inputs).pack(side=tk.RIGHT, padx=10)

        df = tk.Frame(m, bg="#1e1e1e"); df.pack(fill=tk.X, pady=5)
        r1 = tk.Frame(df, bg="#1e1e1e"); r1.pack(fill=tk.X)
        self.entry_pot = self._input(r1, "Pote:", "100"); self.entry_call = self._input(r1, "Call:", "0"); self.entry_stack = self._input(r1, "Stack:", "1000")
        tk.Label(r1, text="Opps:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT, padx=5)
        self.spin_opps = tk.Spinbox(r1, from_=1, to=9, width=3, bg="#333", fg="white"); self.spin_opps.pack(side=tk.LEFT)

        r2 = tk.Frame(df, bg="#1e1e1e"); r2.pack(fill=tk.X, pady=5)
        tk.Label(r2, text="Vilão:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT)
        self.entry_villain = tk.Entry(r2, bg="#333", fg="white", width=10); self.entry_villain.pack(side=tk.LEFT, padx=5)
        self.entry_villain.bind("<FocusOut>", self._carregar_perfil)

        tk.Label(r2, text="Perfil:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT)
        prof_vals = ["Loose", "Standard", "Tight", "Nit"] + list(get_all_custom_ranges().keys())
        self.combo_prof = ttk.Combobox(r2, values=prof_vals, width=12); self.combo_prof.current(0); self.combo_prof.pack(side=tk.LEFT, padx=5)

        tk.Label(r2, text="Pré:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT)
        self.combo_pre = ttk.Combobox(r2, values=["Livre", "Vs Raise", "Vs 3Bet"], width=12); self.combo_pre.current(0); self.combo_pre.pack(side=tk.LEFT)

        if not treino: tk.Button(df, text="CALCULAR", bg="#007acc", fg="white", font=("Segoe UI", 12, "bold"), width=20, command=self._calc).pack(side=tk.RIGHT, padx=20)
        else: tk.Button(df, text="NOVA MÃO", bg="#e040fb", fg="white", width=20, command=self._gerar_treino).pack(side=tk.RIGHT)

        if treino:
            qf = tk.Frame(m, bg="#1e1e1e"); qf.pack(fill=tk.X, pady=5)
            for a, c in [("FOLD","#d32f2f"), ("CHECK/CALL","#fbc02d"), ("BET/RAISE","#388e3c")]:
                tk.Button(qf, text=a, bg=c, width=15, command=lambda x=a: self._check_quiz(x)).pack(side=tk.LEFT, padx=5)
            self.lbl_feed = tk.Label(qf, text="", bg="#1e1e1e", font=("Segoe UI", 12)); self.lbl_feed.pack(side=tk.LEFT, padx=20)

        self.rf = tk.LabelFrame(m, text=" Resultado ", bg="#1e1e1e", fg="white"); self.rf.pack(fill=tk.BOTH, expand=True)
        self.lbl_act = tk.Label(self.rf, text="--", font=("Segoe UI", 24, "bold"), bg="#1e1e1e", fg="white"); self.lbl_act.pack()
        self.lbl_det = tk.Label(self.rf, text="...", bg="#1e1e1e", fg="#aaa", justify=tk.LEFT); self.lbl_det.pack()
        self.bar = ttk.Progressbar(self.rf, length=400); self.bar.pack(pady=5); self.lbl_eq = tk.Label(self.rf, text="", bg="#1e1e1e", fg="white"); self.lbl_eq.pack()

        if not treino:
            self.fin_frame = tk.Frame(self.rf, bg="#1e1e1e"); self.fin_frame.pack(pady=10)
            tk.Button(self.fin_frame, text="💰 VENCI", bg="#2e7d32", fg="white", command=self._win_hand).pack(side=tk.LEFT, padx=10)
            tk.Button(self.fin_frame, text="💀 PERDI", bg="#d32f2f", fg="white", command=self._loss_hand).pack(side=tk.LEFT, padx=10)
            self.fin_frame.pack_forget()

    def _input(self, p, t, d):
        tk.Label(p, text=t, bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT, padx=5)
        e = tk.Entry(p, bg="#333", fg="white", width=8); e.insert(0, d); e.pack(side=tk.LEFT, padx=5)
        return e

    def _carregar_perfil(self, event=None):
        n = self.entry_villain.get().strip()
        if n: 
            p = get_villain_profile(n)
            if p: self.combo_prof.set(p)

    def _criar_slots(self, p):
        hf = tk.Frame(p, bg="#252526"); hf.pack(side=tk.LEFT, padx=10)
        tk.Label(hf, text="Hero", bg="#252526", fg="#aaa").pack()
        self._add_slot(hf, 0); self._add_slot(hf, 1)
        tk.Frame(p, width=2, bg="#444").pack(side=tk.LEFT, fill=tk.Y, padx=10)
        bf = tk.Frame(p, bg="#252526"); bf.pack(side=tk.LEFT)
        tk.Label(bf, text="Board", bg="#252526", fg="#aaa").pack()
        for i in range(2, 7): self._add_slot(bf, i)

    def _add_slot(self, p, i):
        b = tk.Button(p, text="?", font=("Arial", 16), width=4, height=2, bg="#333", fg="#888", command=lambda: self._pop(i))
        b.pack(side=tk.LEFT, padx=2); self.slot_buttons.append(b)

    def _pop(self, i):
        u = [c for k,c in enumerate(self.selected_cards) if c and k!=i]
        CardSelectorPopup(self.root, lambda c: self._set_card(i, c), u)

    def _set_card(self, i, c):
        self.selected_cards[i] = c; b = self.slot_buttons[i]
        if not c:
            b.config(image='', text="?", width=4, height=2, compound='none', state='normal')
        else:
            # USA O CACHE AQUI
            if c in IMG_CACHE_SLOT:
                b.config(image=IMG_CACHE_SLOT[c], text="", width=CARD_SIZE_SLOT[0], height=CARD_SIZE_SLOT[1], compound='center')
            else:
                b.config(text=c)

    def _limpar_inputs(self):
        for i in range(7): self._set_card(i, None)
        self.lbl_act.config(text="--"); self.lbl_det.config(text="...")
        self.bar['value']=0; self.lbl_eq.config(text="")
        if hasattr(self, 'fin_frame'): self.fin_frame.pack_forget()

    def _calc(self):
        h = [c for c in self.selected_cards[0:2] if c]
        b = [c for c in self.selected_cards[2:] if c]
        if len(h)!=2: return messagebox.showwarning("Erro", "Selecione 2 cartas.")
        try:
            pot = float(self.entry_pot.get()); call = float(self.entry_call.get())
            stk = float(self.entry_stack.get()); opps = int(self.spin_opps.get())
            prof = self.combo_prof.get(); pre = self.combo_pre.get()
            v_name = self.entry_villain.get().strip()
        except: return messagebox.showerror("Erro", "Valores inválidos.")
        
        # MUDANÇA VISUAL: CURSOR DE CARREGAMENTO
        self.root.config(cursor="watch"); self.root.update()
        res = analisar_situacao(h, b, pot, call, stk, opps, prof, pre, v_name)
        self.root.config(cursor=""); self.root.update()
        
        if "erro" in res: return messagebox.showerror("Erro", res["erro"])
        self._show_res(res); self.fin_frame.pack(pady=10)

    def _show_res(self, res):
        a = res.get("recommendation", "N/A"); self.lbl_act.config(text=a)
        c = "#ff5555" if "FOLD" in a else "#50fa7b" if "RAISE" in a else "#f1fa8c"
        self.lbl_act.config(fg=c)
        self.lbl_det.config(text=f"Força: {res['hand_strength']}\nDraws: {res['draws']} | Outs: {res['num_outs']}\nRazão: {res['reasoning']}")
        eq = res['equity']; self.bar["value"] = eq; self.lbl_eq.config(text=f"{eq}%")
        st = "Green.Horizontal.TProgressbar" if eq>=60 else "Yellow.Horizontal.TProgressbar" if eq>=40 else "Red.Horizontal.TProgressbar"
        self.bar.configure(style=st)

    def _win_hand(self):
        try:
            pot = float(self.entry_pot.get()); call = float(self.entry_call.get())
            update_bankroll(pot - call, "WIN"); messagebox.showinfo("Boa!", f"Lucro: +${pot-call:.2f}")
            self._limpar_inputs()
        except: pass

    def _loss_hand(self):
        try:
            call = float(self.entry_call.get()); update_bankroll(call, "LOSS")
            messagebox.showinfo("Ops", f"Perda: -${call:.2f}"); self._limpar_inputs()
        except: pass

    def _gerar_treino(self):
        self._limpar_inputs()
        
        # Sorteio simples
        deck = Baralho(); h = deck.deal(2); b = deck.deal(random.choice([3,4,5]))
        
        # ATUALIZAÇÃO VISUAL INSTANTÂNEA (GRAÇAS AO CACHE)
        for i,c in enumerate(h): self._set_card(i, f"{c.valor_str}{c.naipe_str}")
        for i,c in enumerate(b): self._set_card(i+2, f"{c.valor_str}{c.naipe_str}")
        
        p = random.choice([50,100]); c = int(p*0.5) if random.random()>0.4 else 0
        self.entry_pot.delete(0,tk.END); self.entry_pot.insert(0,str(p))
        self.entry_call.delete(0,tk.END); self.entry_call.insert(0,str(c))
        
        # MUDANÇA VISUAL: CURSOR DE CARREGAMENTO DURANTE O CÁLCULO DO GABARITO
        self.root.config(cursor="watch"); self.root.update()
        
        self.current_train_solution = analisar_situacao([f"{c.valor_str}{c.naipe_str}" for c in h], 
                                                        [f"{c.valor_str}{c.naipe_str}" for c in b], 
                                                        p, c, 1000, 1, "Loose", "Livre", None)
                                                        
        self.root.config(cursor=""); self.root.update()

    def _check_quiz(self, ch):
        if not self.current_train_solution: return
        rec = self.current_train_solution["recommendation"]
        win = ("FOLD" in rec and ch=="FOLD") or ("CALL" in rec and "CALL" in ch) or ("RAISE" in rec and "RAISE" in ch)
        log_training_result(ch, rec, win)
        self.lbl_feed.config(text="ACERTOU!" if win else f"ERROU! Era {rec}", fg="#50fa7b" if win else "#ff5555")
        self._show_res(self.current_train_solution)

    def _mostrar_dash(self):
        self._limpar_tela(); f = tk.Frame(self.root, bg="#1e1e1e"); f.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Button(f, text="< Voltar", bg="#333", fg="white", command=self._mostrar_menu_principal).pack(anchor="w")
        hist = get_bankroll_history()
        if hist:
            gf = tk.Frame(f, bg="#1e1e1e"); gf.pack(fill=tk.BOTH, expand=True, pady=20)
            tk.Label(gf, text="GRÁFICO DE BANCA", bg="#1e1e1e", fg="white", font=("Segoe UI", 14)).pack()
            fig, ax = plt.subplots(figsize=(6, 3), dpi=100); fig.patch.set_facecolor('#1e1e1e'); ax.set_facecolor('#1e1e1e')
            ax.plot(hist, color='#50fa7b', marker='o'); ax.tick_params(colors='white'); ax.spines['bottom'].set_color('white'); ax.spines['left'].set_color('white')
            canvas = FigureCanvasTkAgg(fig, master=gf); canvas.draw(); canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else: tk.Label(f, text="Sem dados.", bg="#1e1e1e", fg="#aaa").pack(pady=50)

    def _iniciar_jogo(self): self._construir_ui(False)
    def _iniciar_treino(self): self._construir_ui(True); self._gerar_treino()

class LoginWindow(tk.Toplevel):
    def __init__(self, root, on_success_callback):
        super().__init__(root)
        self.title("Login - GTO Advisor Pro")
        self.geometry("400x550")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        self.on_success = on_success_callback
        
        # Se fechar o login, fecha o app todo
        self.protocol("WM_DELETE_WINDOW", root.destroy)
        
        self._setup_ui()

    def _setup_ui(self):
        # Logo / Branding
        tk.Label(self, text="♠️", font=("Segoe UI", 60), bg="#1e1e1e", fg="#007acc").pack(pady=(40, 10))
        tk.Label(self, text="GTO ADVISOR", font=("Segoe UI", 22, "bold"), bg="#1e1e1e", fg="white").pack()
        tk.Label(self, text="Acesso Profissional", font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaa").pack(pady=(0, 30))

        # Inputs
        frame = tk.Frame(self, bg="#1e1e1e")
        frame.pack(fill="x", padx=40)

        tk.Label(frame, text="E-mail", bg="#1e1e1e", fg="white", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill="x")
        self.entry_email = tk.Entry(frame, bg="#333", fg="white", font=("Segoe UI", 12), insertbackground="white")
        self.entry_email.pack(fill="x", pady=(5, 15), ipady=3)

        tk.Label(frame, text="Senha", bg="#1e1e1e", fg="white", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill="x")
        self.entry_pass = tk.Entry(frame, bg="#333", fg="white", font=("Segoe UI", 12), show="*", insertbackground="white")
        self.entry_pass.pack(fill="x", pady=(5, 20), ipady=3)

        # Botão
        self.btn_login = tk.Button(frame, text="ENTRAR", bg="#007acc", fg="white", font=("Segoe UI", 11, "bold"), 
                                   relief="flat", command=self._fazer_login)
        self.btn_login.pack(fill="x", pady=10, ipady=5)

        # Rodapé
        tk.Label(self, text="Não tem conta?", bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 9)).pack(pady=(20,0))
        lbl_site = tk.Label(self, text="Adquira sua licença aqui", bg="#1e1e1e", fg="#007acc", font=("Segoe UI", 9, "underline"), cursor="hand2")
        lbl_site.pack()
        # lbl_site.bind("<Button-1>", lambda e: webbrowser.open("https://seusite.com"))

    def _fazer_login(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_pass.get().strip()
        
        if not email or not pwd:
            messagebox.showwarning("Atenção", "Preencha todos os campos.")
            return

        self.btn_login.config(text="CONECTANDO...", state="disabled", bg="#333")
        self.update()

        try:
            # 1. Tenta logar na API
            payload = {"email": email, "password": pwd}
            response = requests.post(f"{API_URL}/login", json=payload, timeout=5)
            
            if response.status_code == 200:
                # Sucesso!
                data = response.json()
                token = data.get("access_token")
                # Decodificar o token para saber o plano seria ideal, 
                # mas por enquanto vamos apenas liberar o acesso.
                self.on_success(token)
                self.destroy()
            elif response.status_code == 401:
                messagebox.showerror("Login Falhou", "E-mail ou senha incorretos.")
            elif response.status_code == 400:
                messagebox.showerror("Acesso Negado", "Assinatura inativa ou expirada.")
            else:
                messagebox.showerror("Erro", f"Erro no servidor: {response.status_code}")

        except requests.exceptions.ConnectionError:
            messagebox.showerror("Erro de Conexão", "Não foi possível conectar ao servidor.\nVerifique se o servidor está rodando.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro inesperado: {e}")
        finally:
            self.btn_login.config(text="ENTRAR", state="normal", bg="#007acc")

# --- MAIN MODIFICADO ---
if __name__ == "__main__":
    # Oculta a janela principal do Tkinter inicialmente
    root = tk.Tk()
    root.withdraw() 

    def iniciar_aplicacao(token):
        # Callback chamado quando o login é bem sucedido
        root.deiconify() # Mostra a janela principal
        app = PokerAdvisorApp(root)
        # Aqui você poderia salvar o token no app para usar depois
        # app.auth_token = token 

    # Inicia pela tela de Login
    login_screen = LoginWindow(root, iniciar_aplicacao)
    
    root.mainloop()