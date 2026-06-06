# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
import pymysql
import pyrebase

pymysql.install_as_MySQLdb()

# ─── Firebase ─────────────────────────────────────────────────────────────────
firebase_config = {
    "apiKey": "AIzaSyA8zkZrgGnxJzDTxCr3-gZ96DuGAn5B-OE",
    "authDomain": "serre-connecte-60616.firebaseapp.com",
    "projectId": "serre-connecte-60616",
    "storageBucket": "serre-connecte-60616.firebasestorage.app",
    "messagingSenderId": "217991792040",
    "appId": "1:217991792040:web:ae6fd4a5e0953418aec99d",
    "databaseURL": "https://serre-connecte-60616-default-rtdb.europe-west1.firebasedatabase.app"
}
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# ─── Couleurs ────────────────────────────────────────────────────────────────
C = {
    "bg_main": "#070A13",
    "bg_card": "#0F1524",
    "bg_input": "#161F33",
    "text_main": "#FFFFFF",
    "text_muted": "#6B7A99",
    "accent": "#00E676",
    "danger": "#FF3333",
    "warning": "#FFA000",
    "info": "#00B0FF",
    "border": "#222F47",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def style_btn(btn, bg=None, fg=None):
    btn.configure(
        bg=bg or C["accent"],
        fg=fg or C["bg_main"],
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        cursor="hand2",
        activebackground=C["border"],
        activeforeground=C["text_main"],
        padx=10,
        pady=4
    )

def style_entry(e):
    e.configure(
        bg=C["bg_input"],
        fg=C["text_main"],
        insertbackground=C["text_main"],
        relief="flat",
        font=("Segoe UI", 10),
        highlightthickness=1,
        highlightbackground=C["border"],
        highlightcolor=C["accent"]
    )

# ─── Base de données MariaDB ──────────────────────────────────────────────────
def get_db():
    return pymysql.connect(
        host="localhost",
        user="ravza",
        password="ravza",
        database="serre",
        charset="utf8mb4"
    )

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capteurs (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                uid          VARCHAR(255),
                temperature  FLOAT,
                humidite_air FLOAT,
                humidite_sol FLOAT,
                pluie        BOOLEAN,
                pompe        BOOLEAN DEFAULT 0,
                ventilateur  BOOLEAN DEFAULT 0,
                timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(uid),
                INDEX(timestamp)
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS plantes (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                uid          VARCHAR(255),
                nom          VARCHAR(100),
                temp_max     FLOAT,
                eau_min      FLOAT,
                UNIQUE(uid, nom)
            )""")
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Tables OK ✓")
    except Exception as e:
        print(f"[DB] Erreur: {e}")

# ─── Toggle Switch ────────────────────────────────────────────────────────────
class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, command=None, initial=False, **kwargs):
        self.width = kwargs.pop("width", 70)
        self.height = kwargs.pop("height", 28)
        super().__init__(parent, width=self.width, height=self.height,
                         bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.state = initial
        self.radius = self.height // 2
        self.circle_radius = self.radius - 3
        self.x_on = self.width - self.radius
        self.x_off = self.radius
        self.current_x = self.x_on if initial else self.x_off
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        # Background
        self.create_rectangle(0, 0, self.width, self.height,
                             fill=C["bg_card"], outline=C["border"], width=2)
        # Circle
        color = C["accent"] if self.state else C["text_muted"]
        self.create_oval(self.current_x - self.circle_radius,
                        self.height // 2 - self.circle_radius,
                        self.current_x + self.circle_radius,
                        self.height // 2 + self.circle_radius,
                        fill=color, outline=color)

    def _toggle(self, event=None):
        self.state = not self.state
        target_x = self.x_on if self.state else self.x_off
        steps = 10
        diff = (target_x - self.current_x) / steps

        def step(count):
            if count < steps:
                self.current_x += diff
                self._draw()
                self.after(20, lambda: step(count + 1))
            else:
                self.current_x = target_x
                self._draw()
        step(0)

        if self.command:
            self.command(self.state)

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.current_x = self.x_on if state else self.x_off
            self._draw()

# ─── Page Connexion ───────────────────────────────────────────────────────────
class PageConnexion(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent, bg=C["bg_main"])
        self.on_success = on_success
        self.mode = "connexion"
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=C["bg_card"], height=100)
        header.pack(fill="x", padx=20, pady=20)
        header.pack_propagate(False)

        tk.Label(header, text="🌿 SERRE CONNECTÉE",
                font=("Segoe UI", 24, "bold"),
                bg=C["bg_card"], fg=C["accent"]).pack(anchor="w", pady=(10, 0))
        tk.Label(header, text="Gestion intelligente de votre serre",
                font=("Segoe UI", 10),
                bg=C["bg_card"], fg=C["text_muted"]).pack(anchor="w")

        # Wrapper principal
        self.wrapper = tk.Frame(self, bg=C["bg_main"])
        self.wrapper.pack(fill="both", expand=True, padx=40, pady=40)

        # Onglets
        onglets = tk.Frame(self.wrapper, bg=C["bg_main"])
        onglets.pack(fill="x", pady=(0, 20))

        self.btn_tab_conn = tk.Button(
            onglets, text="CONNEXION",
            command=lambda: self._switch_mode("connexion"),
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=20, pady=6)
        self.btn_tab_conn.pack(side="left", expand=True, fill="x")

        self.btn_tab_insc = tk.Button(
            onglets, text="INSCRIPTION",
            command=lambda: self._switch_mode("inscription"),
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=20, pady=6)
        self.btn_tab_insc.pack(side="left", expand=True, fill="x")

        # Champs
        self.f_fields = tk.Frame(self.wrapper, bg=C["bg_card"])
        self.f_fields.pack(fill="x")

        tk.Label(self.f_fields, text="Adresse email",
                font=("Segoe UI", 9, "bold"),
                bg=C["bg_card"], fg=C["text_muted"]).pack(anchor="w")
        self.e_email = tk.Entry(self.f_fields)
        style_entry(self.e_email)
        self.e_email.pack(fill="x", pady=(4, 14), ipady=8)

        tk.Label(self.f_fields, text="Mot de passe",
                font=("Segoe UI", 9, "bold"),
                bg=C["bg_card"], fg=C["text_muted"]).pack(anchor="w")
        self.e_mdp = tk.Entry(self.f_fields, show="*")
        style_entry(self.e_mdp)
        self.e_mdp.pack(fill="x", pady=(4, 20), ipady=8)

        # Message
        self.lbl_msg = tk.Label(self.wrapper, text="", font=("Segoe UI", 9),
                               bg=C["bg_main"], fg=C["text_muted"])
        self.lbl_msg.pack(pady=10)

        # Bouton submit
        self.btn_submit = tk.Button(self.wrapper, text="SE CONNECTER",
                                   command=self._submit)
        style_btn(self.btn_submit)
        self.btn_submit.pack(fill="x", ipady=10)

        self._update_ui()

    def _switch_mode(self, mode):
        self.mode = mode
        self._update_ui()

    def _update_ui(self):
        if self.mode == "connexion":
            self.btn_tab_conn.configure(bg=C["accent"], fg=C["bg_main"])
            self.btn_tab_insc.configure(bg=C["bg_card"], fg=C["text_muted"])
            self.btn_submit.configure(text="SE CONNECTER")
        else:
            self.btn_tab_conn.configure(bg=C["bg_card"], fg=C["text_muted"])
            self.btn_tab_insc.configure(bg=C["accent"], fg=C["bg_main"])
            self.btn_submit.configure(text="CRÉER MON COMPTE")

    def _submit(self):
        email = self.e_email.get().strip()
        mdp = self.e_mdp.get().strip()

        if not email or not mdp:
            self.lbl_msg.configure(text="Remplissez tous les champs.",
                                 fg=C["danger"])
            return

        self.btn_submit.configure(state="disabled", text="Traitement...")
        self.lbl_msg.configure(text="")

        threading.Thread(target=self._auth_thread, args=(email, mdp),
                        daemon=True).start()

    def _auth_thread(self, email, mdp):
        try:
            if self.mode == "connexion":
                user = auth.sign_in_with_email_and_password(email, mdp)
                uid = user["localId"]
                msg = "✓ Connexion réussie"
            else:
                user = auth.create_user_with_email_and_password(email, mdp)
                uid = user["localId"]
                msg = "✓ Compte créé"

            self._succes(uid, email, msg)

        except Exception as e:
            err = str(e)
            if "EMAIL_EXISTS" in err:
                msg = "Cet email est déjà utilisé."
            elif "INVALID_EMAIL" in err:
                msg = "Email invalide."
            elif "INVALID_PASSWORD" in err or "INVALID_LOGIN_CREDENTIALS" in err:
                msg = "Email ou mot de passe incorrect."
            elif "WEAK_PASSWORD" in err:
                msg = "Mot de passe trop faible (min 6 caractères)."
            else:
                msg = "Erreur de connexion."
            self.after(0, self._erreur, msg)

    def _succes(self, uid, email, msg):
        self.lbl_msg.configure(text=msg, fg=C["accent"])
        self.after(800, lambda: self.on_success(uid, email))

    def _erreur(self, msg):
        self.lbl_msg.configure(text=msg, fg=C["danger"])
        txt = "SE CONNECTER" if self.mode == "connexion" else "CRÉER MON COMPTE"
        self.btn_submit.configure(state="normal", text=txt)

# ─── Page Dashboard ───────────────────────────────────────────────────────────
class PageDashboard(tk.Frame):
    def __init__(self, parent, uid, email, on_deconn):
        super().__init__(parent, bg=C["bg_main"])
        self.uid = uid
        self.email = email
        self.on_deconn = on_deconn
        
        self.temp = 0
        self.hum = 0
        self.sol = 0
        self.pluie = False
        self.pompe_on = False
        self.ventilo_on = False
        
        self._build_layout()
        self._rafraichir_donnees()

    def _build_layout(self):
        # Header
        header = tk.Frame(self, bg=C["bg_card"])
        header.pack(fill="x", padx=20, pady=10)

        tk.Label(header, text=f"🌿 {self.email}",
                font=("Segoe UI", 14, "bold"),
                bg=C["bg_card"], fg=C["accent"]).pack(side="left", padx=10)

        btn_deconn = tk.Button(header, text="DÉCONNEXION",
                              command=self.on_deconn)
        style_btn(btn_deconn, bg=C["danger"])
        btn_deconn.pack(side="right", padx=10)

        # Body
        body = tk.Frame(self, bg=C["bg_main"])
        body.pack(fill="both", expand=True, padx=15, pady=15)

        # Cartes capteurs
        cards = tk.Frame(body, bg=C["bg_main"])
        cards.pack(fill="x", pady=(0, 20))

        # Card Temperature
        card_temp = self._make_card(cards, "🌡️ Température")
        self.lbl_temp = tk.Label(card_temp, text="-- °C",
                                font=("Segoe UI", 24, "bold"),
                                bg=C["bg_card"], fg=C["accent"])
        self.lbl_temp.pack(pady=10)

        # Card Humidité Air
        card_hum = self._make_card(cards, "💧 Humidité Air")
        self.lbl_hum = tk.Label(card_hum, text="-- %",
                               font=("Segoe UI", 24, "bold"),
                               bg=C["bg_card"], fg=C["accent"])
        self.lbl_hum.pack(pady=10)

        # Card Humidité Sol
        card_sol = self._make_card(cards, "🌱 Humidité Sol")
        self.lbl_sol = tk.Label(card_sol, text="-- %",
                               font=("Segoe UI", 24, "bold"),
                               bg=C["bg_card"], fg=C["accent"])
        self.lbl_sol.pack(pady=10)

        # Card Pluie
        card_pluie = self._make_card(cards, "🌧️ Pluie")
        self.lbl_pluie = tk.Label(card_pluie, text="-- ",
                                 font=("Segoe UI", 24, "bold"),
                                 bg=C["bg_card"], fg=C["accent"])
        self.lbl_pluie.pack(pady=10)

        # Contrôles
        ctrl_frame = tk.Frame(body, bg=C["bg_main"])
        ctrl_frame.pack(fill="x", pady=20)

        # Pompe
        f_pompe = tk.Frame(ctrl_frame, bg=C["bg_card"], padx=15, pady=15)
        f_pompe.pack(side="left", expand=True, padx=10, fill="both")

        tk.Label(f_pompe, text="💧 Pompe",
                font=("Segoe UI", 11, "bold"),
                bg=C["bg_card"], fg=C["text_main"]).pack(anchor="w")
        
        self.toggle_pompe = ToggleSwitch(f_pompe, command=self._api_pompe,
                                        initial=False)
        self.toggle_pompe.pack(anchor="w", pady=(10, 0))

        # Ventilateur
        f_ventilo = tk.Frame(ctrl_frame, bg=C["bg_card"], padx=15, pady=15)
        f_ventilo.pack(side="left", expand=True, padx=10, fill="both")

        tk.Label(f_ventilo, text="💨 Ventilateur",
                font=("Segoe UI", 11, "bold"),
                bg=C["bg_card"], fg=C["text_main"]).pack(anchor="w")
        
        self.toggle_ventilo = ToggleSwitch(f_ventilo, command=self._api_ventilo,
                                          initial=False)
        self.toggle_ventilo.pack(anchor="w", pady=(10, 0))

        # Console
        console_frame = tk.Frame(body, bg=C["bg_main"])
        console_frame.pack(fill="both", expand=True, pady=(20, 0))

        tk.Label(console_frame, text="📊 Historique",
                font=("Segoe UI", 11, "bold"),
                bg=C["bg_main"], fg=C["accent"]).pack(anchor="w", pady=(0, 10))

        self.table = ttk.Treeview(console_frame, height=8, columns=("Time", "T", "H", "Sol", "Pluie"),
                                 show="headings")
        self.table.heading("Time", text="Heure")
        self.table.heading("T", text="Temp")
        self.table.heading("H", text="Humidité")
        self.table.heading("Sol", text="Sol")
        self.table.heading("Pluie", text="Pluie")

        self.table.column("Time", width=120)
        self.table.column("T", width=80)
        self.table.column("H", width=80)
        self.table.column("Sol", width=80)
        self.table.column("Pluie", width=80)

        self.table.pack(fill="both", expand=True)

    def _make_card(self, parent, title):
        card = tk.Frame(parent, bg=C["bg_card"], padx=15, pady=10)
        card.pack(side="left", expand=True, fill="both", padx=5)

        tk.Label(card, text=title,
                font=("Segoe UI", 10, "bold"),
                bg=C["bg_card"], fg=C["text_muted"]).pack(anchor="w")

        return card

    def _rafraichir_donnees(self):
        """Lit depuis MariaDB et affiche"""
        def _fetch():
            try:
                conn = get_db()
                cur = conn.cursor()

                # Dernière lecture
                cur.execute(
                    "SELECT temperature, humidite_air, humidite_sol, pluie, pompe, ventilateur "
                    "FROM capteurs WHERE uid=%s ORDER BY id DESC LIMIT 1",
                    (self.uid,)
                )
                row = cur.fetchone()

                if row:
                    self.temp = row[0] or 0
                    self.hum = row[1] or 0
                    self.sol = row[2] or 0
                    self.pluie = row[3] or False
                    self.pompe_on = row[4] or False
                    self.ventilo_on = row[5] or False

                    self.after(0, self._afficher_capteurs)

                # Historique (derniers 5)
                cur.execute(
                    "SELECT timestamp, temperature, humidite_air, humidite_sol, pluie "
                    "FROM capteurs WHERE uid=%s ORDER BY id DESC LIMIT 5",
                    (self.uid,)
                )
                rows = cur.fetchall()

                for item in self.table.get_children():
                    self.table.delete(item)

                for r in rows:
                    date_str = r[0].strftime("%H:%M:%S") if r[0] else "--"
                    pluie_str = "OUI 🌧️" if r[4] else "NON ☀️"
                    self.table.insert("", "end",
                        values=(date_str,
                                f"{r[1] or '--'} °C",
                                f"{r[2] or '--'} %",
                                f"{r[3] or '--'} %",
                                pluie_str))

                cur.close()
                conn.close()

            except Exception as e:
                print(f"[MariaDB] Erreur: {e}")

        threading.Thread(target=_fetch, daemon=True).start()
        self.after(2000, self._rafraichir_donnees)

    def _afficher_capteurs(self):
        self.lbl_temp.configure(text=f"{self.temp:.1f} °C")
        self.lbl_hum.configure(text=f"{self.hum:.0f} %")
        self.lbl_sol.configure(text=f"{self.sol:.0f} %")
        self.lbl_pluie.configure(
            text="OUI 🌧️" if self.pluie else "NON ☀️",
            fg=C["danger"] if self.pluie else C["accent"]
        )

    def _api_pompe(self, state):
        self.pompe_on = state
        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update(
                {"pompe": state}),
            daemon=True).start()

    def _api_ventilo(self, state):
        self.ventilo_on = state
        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update(
                {"ventilateur": state}),
            daemon=True).start()

# ─── Application principale ───────────────────────────────────────────────────
class App:
    def __init__(self):
        self.fen = tk.Tk()
        self.fen.title("Serre Connected")
        self.fen.geometry("1000x700")
        self.fen.configure(bg=C["bg_main"])
        self.fen.resizable(False, False)
        
        init_db()
        self.page = None
        self._connexion()

    def _connexion(self):
        if self.page:
            self.page.destroy()
        self.page = PageConnexion(self.fen, self._dashboard)
        self.page.pack(fill="both", expand=True)

    def _dashboard(self, uid, email):
        if self.page:
            self.page.destroy()
        self.page = PageDashboard(self.fen, uid, email, self._connexion)
        self.page.pack(fill="both", expand=True)

    def run(self):
        self.fen.mainloop()

if __name__ == "__main__":
    App().run()
