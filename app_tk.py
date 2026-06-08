# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
import threading
import time
import pymysql
pymysql.install_as_MySQLdb()
import pyrebase

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
auth     = firebase.auth()
db       = firebase.database()

# ─── Base de données ──────────────────────────────────────
def get_db():
    return pymysql.connect(host="localhost", user="ravza",
                           password="ravza", database="serre",
                           charset="utf8mb4")

def init_db():
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS capteurs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255), temperature FLOAT,
            humidite_air FLOAT, humidite_sol FLOAT,
            pluie BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS plantes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255), nom VARCHAR(100),
            temp_max FLOAT, humidite_min FLOAT, eau_min FLOAT)""")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[DB] Erreur init: {e}")

# ─── Palette de couleurs ──────────────────────────────────
C = {
    "fond":      "#0a0f1e",
    "fond2":     "#0d1529",
    "carte":     "#111d35",
    "carte2":    "#162040",
    "carte3":    "#1a2650",
    "texte":     "#e8f4f8",
    "gris":      "#4a6fa5",
    "gris2":     "#1e2d50",
    "vert":      "#00ff88",
    "vert2":     "#00cc6a",
    "rouge":     "#ff4757",
    "orange":    "#ffa502",
    "bleu":      "#1e90ff",
    "accent":    "#00d4aa",
    "accent2":   "#009977",
    "titre":     "#00d4aa",
    "console":   "#050d1a",
    "log_info":  "#00d4aa",
    "log_warn":  "#ffa502",
    "log_err":   "#ff4757",
    "log_ok":    "#00ff88",
}

# ─── Helpers style ────────────────────────────────────────
def bs(w, bg=C["accent"], fg=C["fond"], sz=10):
    w.configure(bg=bg, fg=fg, font=("Courier", sz, "bold"),
                relief="flat", bd=0, cursor="hand2",
                activebackground=C["accent2"], activeforeground=C["fond"])

def es(w):
    w.configure(bg=C["gris2"], fg=C["texte"], font=("Courier", 10),
                relief="flat", bd=0, insertbackground=C["accent"],
                selectbackground=C["accent"])

# ─── Page Connexion ───────────────────────────────────────
class PageConnexion(tk.Frame):
    def __init__(self, parent, on_conn):
        super().__init__(parent, bg=C["fond"])
        self.on_conn = on_conn
        self.mode    = "connexion"
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        wrap = tk.Frame(self, bg=C["fond"])
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrap, text="◈ SERRE CONNECTEE",
                 font=("Courier", 22, "bold"),
                 bg=C["fond"], fg=C["accent"]).pack(pady=(0, 4))
        tk.Label(wrap, text="Systeme de monitoring IoT",
                 font=("Courier", 10),
                 bg=C["fond"], fg=C["gris"]).pack()
        tk.Frame(wrap, bg=C["accent"], height=2).pack(fill="x", pady=(16, 20))

        card = tk.Frame(wrap, bg=C["carte"], padx=30, pady=30)
        card.pack(ipadx=10, ipady=10)

        # Onglets
        tabs = tk.Frame(card, bg=C["carte"])
        tabs.pack(fill="x", pady=(0, 20))
        self.btn_co = tk.Button(tabs, text="CONNEXION", command=lambda: self._tab("connexion"),
                                font=("Courier", 10, "bold"), relief="flat", bd=0,
                                cursor="hand2", pady=8, padx=20)
        self.btn_co.configure(bg=C["accent"], fg=C["fond"])
        self.btn_co.pack(side="left")
        self.btn_in = tk.Button(tabs, text="INSCRIPTION", command=lambda: self._tab("inscription"),
                                font=("Courier", 10, "bold"), relief="flat", bd=0,
                                cursor="hand2", pady=8, padx=20)
        self.btn_in.configure(bg=C["gris2"], fg=C["gris"])
        self.btn_in.pack(side="left", padx=(4, 0))

        # Champs
        for label, attr in [("Email", "e_email"), ("Mot de passe", "e_mdp")]:
            tk.Label(card, text=label, font=("Courier", 9),
                     bg=C["carte"], fg=C["gris"]).pack(anchor="w")
            e = tk.Entry(card, width=32, show="*" if "mdp" in attr else "")
            es(e)
            e.pack(fill="x", ipady=8, pady=(2, 12))
            setattr(self, attr, e)

        self.btn_ok = tk.Button(card, text="[ SE CONNECTER ]",
                                command=self._action, pady=12)
        bs(self.btn_ok, sz=11)
        self.btn_ok.pack(fill="x", pady=(8, 0))

        self.lbl_msg = tk.Label(card, text="",
                                font=("Courier", 9),
                                bg=C["carte"], fg=C["rouge"])
        self.lbl_msg.pack(pady=(10, 0))
        tk.Frame(card, bg=C["accent"], height=2).pack(fill="x", pady=(20, 0))

        tk.Label(wrap, text="[ Raspberry Pi 4 | Debian Trixie | IoT ]",
                 font=("Courier", 8), bg=C["fond"], fg=C["gris2"]).pack(pady=(12, 0))

    def _tab(self, mode):
        self.mode = mode
        if mode == "connexion":
            self.btn_co.configure(bg=C["accent"], fg=C["fond"])
            self.btn_in.configure(bg=C["gris2"],  fg=C["gris"])
            if hasattr(self, "btn_ok"):
                self.btn_ok.configure(text="[ SE CONNECTER ]")
        else:
            self.btn_in.configure(bg=C["accent"], fg=C["fond"])
            self.btn_co.configure(bg=C["gris2"],  fg=C["gris"])
            if hasattr(self, "btn_ok"):
                self.btn_ok.configure(text="[ CREER UN COMPTE ]")

    def _action(self):
        email = self.e_email.get().strip()
        mdp   = self.e_mdp.get().strip()
        if not email or not mdp:
            self.lbl_msg.configure(text="[!] Remplissez tous les champs")
            return
        self.btn_ok.configure(text="...", state="disabled")
        self.lbl_msg.configure(text="")

        def tache():
            try:
                if self.mode == "connexion":
                    user = auth.sign_in_with_email_and_password(email, mdp)
                else:
                    user = auth.create_user_with_email_and_password(email, mdp)
                uid = user["localId"]
                self.after(0, lambda: self.on_conn(uid, email))
            except Exception as e:
                s   = str(e)
                msg = "[!] Email ou mot de passe incorrect"
                if   "EMAIL_EXISTS"    in s: msg = "[!] Email deja utilise"
                elif "WEAK_PASSWORD"   in s: msg = "[!] Mot de passe trop court (6 min)"
                elif "INVALID_EMAIL"   in s: msg = "[!] Email invalide"
                t = "[ SE CONNECTER ]" if self.mode == "connexion" else "[ CREER UN COMPTE ]"
                self.after(0, lambda: [
                    self.lbl_msg.configure(text=msg),
                    self.btn_ok.configure(text=t, state="normal")
                ])
        threading.Thread(target=tache, daemon=True).start()

# ─── Page Dashboard ───────────────────────────────────────
class PageDashboard(tk.Frame):
    def __init__(self, parent, uid, email, on_deconn):
        super().__init__(parent, bg=C["fond"])
        self.uid           = uid
        self.email         = email
        self.on_deconn     = on_deconn
        self.plantes       = []
        self.plante_active = None
        self.pompe_on      = False
        self.ventilo_on    = False
        self._charger_plantes()
        self._build()
        self._rafraichir()

    def _charger_plantes(self):
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute(
                "SELECT nom,temp_max,humidite_min,eau_min FROM plantes WHERE uid=%s",
                (self.uid,))
            self.plantes = [
                {"nom": r[0], "temp_max": r[1],
                 "humidite_min": r[2], "eau_min": r[3]}
                for r in cur.fetchall()
            ]
            cur.close(); conn.close()
        except:
            self.plantes = []
        if self.plantes:
            self.plante_active = self.plantes[0]

    def _card(self, parent, titre):
        f = tk.Frame(parent, bg=C["carte"], padx=16, pady=14)
        f.pack(fill="x", pady=(0, 10))
        tk.Label(f, text=titre, font=("Courier", 10, "bold"),
                 bg=C["carte"], fg=C["accent"]).pack(anchor="w", pady=(0, 10))
        tk.Frame(f, bg=C["gris2"], height=1).pack(fill="x", pady=(0, 10))
        return f

    def _build(self):
        # ── Barre du haut ─────────────────────────────────
        top = tk.Frame(self, bg=C["fond2"], pady=10)
        top.pack(fill="x")

        tk.Label(top, text="◈ SERRE CONNECTEE",
                 font=("Courier", 14, "bold"),
                 bg=C["fond2"], fg=C["accent"]).pack(side="left", padx=18)

        self.lbl_connexion = tk.Label(top, text="● CONNEXION...",
                                      font=("Courier", 9),
                                      bg=C["fond2"], fg=C["orange"])
        self.lbl_connexion.pack(side="left", padx=10)

        tk.Label(top, text=f"[ {self.email} ]",
                 font=("Courier", 9),
                 bg=C["fond2"], fg=C["gris"]).pack(side="left", padx=10)

        btn_deconn = tk.Button(top, text="[DECONNEXION]",
                               command=self.on_deconn, pady=6, padx=12)
        bs(btn_deconn, bg=C["rouge"], fg=C["texte"])
        btn_deconn.pack(side="right", padx=18)

        # ── Corps principal : gauche + droite ─────────────
        corps = tk.Frame(self, bg=C["fond"])
        corps.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Colonne GAUCHE (scroll) ───────────────────────
        left_wrap = tk.Frame(corps, bg=C["fond"], width=520)
        left_wrap.pack(side="left", fill="both", expand=True, padx=(0, 8))
        left_wrap.pack_propagate(False)

        canvas = tk.Canvas(left_wrap, bg=C["fond"], highlightthickness=0)
        sb = tk.Scrollbar(left_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(canvas, bg=C["fond"])
        win_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        self.inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        self._section_capteurs()
        self._section_actionneurs()
        self._section_plantes()

        self.lbl_statut = tk.Label(self.inner, text="",
                                   font=("Courier", 8),
                                   bg=C["fond"], fg=C["gris"])
        self.lbl_statut.pack(pady=5)

        # ── Colonne DROITE (historique) ───────────────────
        right = tk.Frame(corps, bg=C["carte"], width=380)
        right.pack(side="right", fill="both", padx=(8, 0))
        right.pack_propagate(False)

        tk.Label(right, text=">> HISTORIQUE / LOGS",
                 font=("Courier", 10, "bold"),
                 bg=C["carte"], fg=C["accent"]).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Frame(right, bg=C["gris2"], height=1).pack(fill="x", padx=12, pady=(0, 6))

        cf = tk.Frame(right, bg=C["console"])
        cf.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self.console = tk.Text(cf, bg=C["console"], fg=C["log_info"],
                               font=("Courier", 8), relief="flat", bd=0,
                               state="disabled", wrap="word",
                               insertbackground=C["accent"])
        sb_c = tk.Scrollbar(cf, command=self.console.yview)
        self.console.configure(yscrollcommand=sb_c.set)
        sb_c.pack(side="right", fill="y")
        self.console.pack(fill="both", expand=True, padx=4, pady=4)

        self.console.tag_configure("INFO",  foreground=C["log_info"])
        self.console.tag_configure("OK",    foreground=C["log_ok"])
        self.console.tag_configure("WARN",  foreground=C["log_warn"])
        self.console.tag_configure("ERROR", foreground=C["log_err"])
        self.console.tag_configure("DATA",  foreground=C["texte"])
        self.console.tag_configure("TIME",  foreground=C["gris"])

        btn_clear = tk.Button(right, text="[EFFACER]",
                              command=self._clear_console, pady=5)
        bs(btn_clear, bg=C["gris2"], fg=C["gris"])
        btn_clear.pack(fill="x", padx=8, pady=(0, 8))

        self._log("INFO", "Systeme demarre")
        self._log("INFO", f"User: {self.email}")
        self._log("INFO", f"UID : {self.uid[:12]}...")
        self._log("INFO", "En attente des capteurs...")

    def _log(self, niveau, msg):
        self.console.configure(state="normal")
        t = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{t}] ", "TIME")
        self.console.insert("end", f"[{niveau}] {msg}\n", niveau)
        self.console.see("end")
        self.console.configure(state="disabled")

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _section_capteurs(self):
        card   = self._card(self.inner, ">> CAPTEURS EN TEMPS REEL")
        grille = tk.Frame(card, bg=C["carte"])
        grille.pack(fill="x")
        self._vals = {}
        donnees = [
            ("TEMPERATURE", "temp",  "--", "C",  "T"),
            ("HUMID. AIR",  "hum",   "--", "%",  "H"),
            ("HUMID. SOL",  "sol",   "--", "%",  "S"),
            ("PLUIE",       "pluie", "--", "",   "P"),
        ]
        for i, (nom, key, val, unit, ico) in enumerate(donnees):
            c = tk.Frame(grille, bg=C["carte2"], padx=12, pady=10)
            c.grid(row=i//2, column=i%2, padx=4, pady=4, sticky="ew")
            grille.columnconfigure(i%2, weight=1)
            tk.Label(c, text=f"[{ico}] {nom}",
                     font=("Courier", 8),
                     bg=C["carte2"], fg=C["gris"]).pack(anchor="w")
            lbl = tk.Label(c, text=f"{val}{unit}",
                           font=("Courier", 20, "bold"),
                           bg=C["carte2"], fg=C["texte"])
            lbl.pack(anchor="w", pady=(4, 2))
            bar_bg = tk.Frame(c, bg=C["gris2"], height=3)
            bar_bg.pack(fill="x")
            bar = tk.Frame(bar_bg, bg=C["accent"], height=3)
            bar.place(x=0, y=0, relheight=1, relwidth=0.5)
            self._vals[key] = (lbl, bar)

    def _section_actionneurs(self):
        card   = self._card(self.inner, ">> ACTIONNEURS")
        grille = tk.Frame(card, bg=C["carte"])
        grille.pack(fill="x")
        for col, (nom, tog, lbl_a, btn_a) in enumerate([
            ("POMPE",       self._tog_pompe,   "lbl_pompe",   "btn_pompe"),
            ("VENTILATEUR", self._tog_ventilo, "lbl_ventilo", "btn_ventilo"),
        ]):
            c = tk.Frame(grille, bg=C["carte2"], padx=14, pady=14)
            c.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
            grille.columnconfigure(col, weight=1)
            tk.Label(c, text=nom, font=("Courier", 10, "bold"),
                     bg=C["carte2"], fg=C["gris"]).pack()
            lbl = tk.Label(c, text="[OFF]",
                           font=("Courier", 13, "bold"),
                           bg=C["carte2"], fg=C["rouge"])
            lbl.pack(pady=8)
            btn = tk.Button(c, text="[ACTIVER]", command=tog, pady=7)
            bs(btn)
            btn.pack(fill="x")
            setattr(self, lbl_a, lbl)
            setattr(self, btn_a, btn)

    def _section_plantes(self):
        self._afficher_plantes()

    def _afficher_plantes(self):
        if hasattr(self, "_card_plantes") and self._card_plantes.winfo_exists():
            self._card_plantes.destroy()

        card = self._card(self.inner, ">> MES PLANTES")
        self._card_plantes = card

        btn_add = tk.Button(card, text="[+ AJOUTER UNE PLANTE]",
                            command=self._popup_plante, pady=7)
        bs(btn_add, sz=9)
        btn_add.pack(fill="x", pady=(0, 10))

        if not self.plantes:
            tk.Label(card, text="Aucune plante enregistree",
                     font=("Courier", 9), bg=C["carte"], fg=C["gris"]).pack()
            return

        for p in self.plantes:
            actif = self.plante_active and self.plante_active["nom"] == p["nom"]
            ibg   = C["carte3"] if actif else C["carte2"]
            inner = tk.Frame(card, bg=ibg, padx=12, pady=10)
            inner.pack(fill="x", pady=(0, 6))

            head = tk.Frame(inner, bg=ibg)
            head.pack(fill="x")
            tk.Label(head, text=f"◉ {p['nom']}" if actif else f"○ {p['nom']}",
                     font=("Courier", 11, "bold"),
                     bg=ibg, fg=C["accent"] if actif else C["texte"]).pack(side="left")
            if actif:
                tk.Label(head, text=" [ACTIVE]",
                         font=("Courier", 8),
                         bg=ibg, fg=C["vert"]).pack(side="left")

            info = tk.Frame(inner, bg=ibg)
            info.pack(fill="x", pady=(6, 0))
            for txt in [f"T.max:{p['temp_max']}C",
                        f"Hum:{p['humidite_min']}%",
                        f"Eau:{p['eau_min']}%"]:
                chip = tk.Frame(info, bg=C["gris2"], padx=7, pady=3)
                chip.pack(side="left", padx=(0, 5))
                tk.Label(chip, text=txt, font=("Courier", 8),
                         bg=C["gris2"], fg=C["texte"]).pack()

            btns = tk.Frame(inner, bg=ibg)
            btns.pack(fill="x", pady=(8, 0))
            if not actif:
                b = tk.Button(btns, text="[SELECT]",
                              command=lambda pl=p: self._select(pl),
                              pady=4, padx=8)
                bs(b, sz=9)
                b.pack(side="left")
            b2 = tk.Button(btns, text="[SUPPR]",
                           command=lambda pl=p: self._suppr(pl),
                           pady=4, padx=8)
            bs(b2, bg=C["rouge"], fg=C["texte"], sz=9)
            b2.pack(side="right")

    def _popup_plante(self):
        if len(self.plantes) >= 3:
            messagebox.showwarning("Limite", "Maximum 3 plantes !")
            return
        pop = tk.Toplevel(self)
        pop.title("Nouvelle plante")
        pop.configure(bg=C["fond"])
        pop.geometry("400x460")
        pop.resizable(False, False)
        pop.grab_set()

        card = tk.Frame(pop, bg=C["carte"], padx=24, pady=24)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text=">> NOUVELLE PLANTE",
                 font=("Courier", 12, "bold"),
                 bg=C["carte"], fg=C["accent"]).pack(anchor="w", pady=(0, 14))

        fields = [
            ("Nom de la plante", "nom",          ""),
            ("Temperature max (C)", "temp_max",  "30"),
            ("Humidite min (%)",    "humidite_min", "40"),
            ("Humidite sol min (%)", "eau_min",   "30"),
        ]
        entries = {}
        for label, key, default in fields:
            tk.Label(card, text=label, font=("Courier", 9),
                     bg=C["carte"], fg=C["gris"]).pack(anchor="w")
            e = tk.Entry(card, width=30)
            es(e)
            e.insert(0, default)
            e.pack(fill="x", ipady=7, pady=(2, 10))
            entries[key] = e

        lbl_err = tk.Label(card, text="", font=("Courier", 9),
                           bg=C["carte"], fg=C["rouge"])
        lbl_err.pack()

        def save():
            nom = entries["nom"].get().strip()
            if not nom:
                lbl_err.configure(text="[!] Nom obligatoire"); return
            if any(p["nom"].lower() == nom.lower() for p in self.plantes):
                lbl_err.configure(text="[!] Plante deja existante"); return
            try:
                tm = float(entries["temp_max"].get())
                hm = float(entries["humidite_min"].get())
                em = float(entries["eau_min"].get())
            except:
                lbl_err.configure(text="[!] Valeurs invalides"); return
            try:
                conn = get_db(); cur = conn.cursor()
                cur.execute(
                    "INSERT INTO plantes (uid,nom,temp_max,humidite_min,eau_min) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (self.uid, nom, tm, hm, em))
                conn.commit(); cur.close(); conn.close()
            except Exception as e:
                lbl_err.configure(text=f"[!] DB: {e}"); return
            self.plantes.append(
                {"nom": nom, "temp_max": tm, "humidite_min": hm, "eau_min": em})
            if not self.plante_active:
                self.plante_active = self.plantes[0]
            self._rebuild()
            self._log("OK", f"Plante ajoutee: {nom}")
            pop.destroy()

        btn = tk.Button(card, text="[AJOUTER]", command=save, pady=10)
        bs(btn, sz=11)
        btn.pack(fill="x", pady=(8, 0))

    def _rebuild(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._section_capteurs()
        self._section_actionneurs()
        self._section_plantes()
        self.lbl_statut = tk.Label(self.inner, text="",
                                   font=("Courier", 8),
                                   bg=C["fond"], fg=C["gris"])
        self.lbl_statut.pack(pady=5)

    def _select(self, p):
        self.plante_active = p
        self._afficher_plantes()
        self._log("INFO", f"Plante: {p['nom']}")

    def _suppr(self, p):
        if not messagebox.askyesno("Supprimer", f"Supprimer {p['nom']} ?"):
            return
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute(
                "DELETE FROM plantes WHERE uid=%s AND nom=%s",
                (self.uid, p["nom"]))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            self._log("ERROR", f"Suppression: {e}")
        self.plantes = [x for x in self.plantes if x["nom"] != p["nom"]]
        if self.plante_active and self.plante_active["nom"] == p["nom"]:
            self.plante_active = self.plantes[0] if self.plantes else None
        self._rebuild()
        self._log("WARN", f"Plante supprimee: {p['nom']}")

    def _tog_pompe(self):
        self.pompe_on = not self.pompe_on
        if self.pompe_on:
            self.lbl_pompe.configure(text="[ON]",  fg=C["vert"])
            self.btn_pompe.configure(text="[DESACTIVER]",
                                     bg=C["rouge"], fg=C["texte"])
            self._log("OK", "Pompe activee manuellement")
        else:
            self.lbl_pompe.configure(text="[OFF]", fg=C["rouge"])
            self.btn_pompe.configure(text="[ACTIVER]",
                                     bg=C["accent"], fg=C["fond"])
            self._log("WARN", "Pompe desactivee manuellement")
        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update(
                {"pompe": self.pompe_on}),
            daemon=True).start()

    def _tog_ventilo(self):
        self.ventilo_on = not self.ventilo_on
        if self.ventilo_on:
            self.lbl_ventilo.configure(text="[ON]",  fg=C["vert"])
            self.btn_ventilo.configure(text="[DESACTIVER]",
                                       bg=C["rouge"], fg=C["texte"])
            self._log("OK", "Ventilateur active manuellement")
        else:
            self.lbl_ventilo.configure(text="[OFF]", fg=C["rouge"])
            self.btn_ventilo.configure(text="[ACTIVER]",
                                       bg=C["accent"], fg=C["fond"])
            self._log("WARN", "Ventilateur desactive manuellement")
        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update(
                {"ventilateur": self.ventilo_on}),
            daemon=True).start()

    def _rafraichir(self):
        self._log("INFO", "Connexion Firebase...")
        self._rafraichir_poll()

    def _rafraichir_poll(self):
        def tache():
            try:
                d = db.child("capteurs").child(self.uid).get().val()
                if d:
                    self.after(0, self._update, d)
                    self._save_db(d)
                    self.after(0, self._sync_actionneurs, d)
                    self.after(0, lambda: self.lbl_connexion.configure(
                        text="● CAPTEURS", fg=C["vert"]))
                else:
                    self._log("WARN", "Aucune donnee Firebase")
                    self.after(0, lambda: self.lbl_connexion.configure(
                        text="● EN ATTENTE", fg=C["orange"]))
            except Exception as e:
                self._log("ERROR", f"Firebase: {e}")
                self.after(0, lambda: self.lbl_connexion.configure(
                    text="● ERREUR", fg=C["rouge"]))
            self.after(5000, self._rafraichir_poll)
        threading.Thread(target=tache, daemon=True).start()

    def _sync_actionneurs(self, d):
        pompe_on   = d.get("pompe",       False)
        ventilo_on = d.get("ventilateur", False)
        if pompe_on:
            self.lbl_pompe.configure(text="[ON]",  fg=C["vert"])
            self.btn_pompe.configure(text="[DESACTIVER]",
                                     bg=C["rouge"], fg=C["texte"])
        else:
            self.lbl_pompe.configure(text="[OFF]", fg=C["rouge"])
            self.btn_pompe.configure(text="[ACTIVER]",
                                     bg=C["accent"], fg=C["fond"])
        self.pompe_on = pompe_on

        if ventilo_on:
            self.lbl_ventilo.configure(text="[ON]",  fg=C["vert"])
            self.btn_ventilo.configure(text="[DESACTIVER]",
                                       bg=C["rouge"], fg=C["texte"])
        else:
            self.lbl_ventilo.configure(text="[OFF]", fg=C["rouge"])
            self.btn_ventilo.configure(text="[ACTIVER]",
                                       bg=C["accent"], fg=C["fond"])
        self.ventilo_on = ventilo_on

    def _save_db(self, d):
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute(
                "INSERT INTO capteurs "
                "(uid,temperature,humidite_air,humidite_sol,pluie) "
                "VALUES (%s,%s,%s,%s,%s)",
                (self.uid,
                 d.get("temperature"),
                 d.get("humidite_air"),
                 d.get("humidite_sol"),
                 d.get("pluie", False)))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            self._log("ERROR", f"MariaDB: {e}")

    def _update(self, d):
        temp  = d.get("temperature",  "--")
        hum   = d.get("humidite_air", "--")
        sol   = d.get("humidite_sol", "--")
        pluie = d.get("pluie",        False)

        configs = {
            "temp": (
                f"{temp}C",
                C["rouge"] if isinstance(temp, (int, float)) and temp > 30
                           else C["vert"],
                min(temp / 50, 1) if isinstance(temp, (int, float)) else 0.5
            ),
            "hum": (
                f"{hum}%",
                C["orange"] if isinstance(hum, (int, float)) and hum < 40
                            else C["vert"],
                hum / 100 if isinstance(hum, (int, float)) else 0.5
            ),
            "sol": (
                f"{sol}%",
                C["rouge"] if isinstance(sol, (int, float)) and sol < 30
                           else C["vert"],
                sol / 100 if isinstance(sol, (int, float)) else 0.5
            ),
            "pluie": (
                "OUI" if pluie else "NON",
                C["bleu"] if pluie else C["gris"],
                1.0 if pluie else 0.05
            ),
        }
        for key, (txt, color, ratio) in configs.items():
            lbl, bar = self._vals[key]
            lbl.configure(text=txt, fg=color)
            bar.configure(bg=color)
            bar.place(relwidth=min(max(ratio, 0), 1))

        self._log("DATA",
                  f"T:{temp}C H:{hum}% Sol:{sol}% "
                  f"Pluie:{'OUI' if pluie else 'NON'}")
        self.lbl_statut.configure(
            text=f"[{time.strftime('%H:%M:%S')}] Derniere mise a jour",
            fg=C["gris"])

        if self.plante_active and isinstance(temp, (int, float)):
            p = self.plante_active
            if temp > p["temp_max"]:
                self._log("WARN",
                          f"[ALERTE] {p['nom']} : Temperature trop haute ! "
                          f"({temp}C > {p['temp_max']}C)")
            if isinstance(hum, (int, float)) and hum < p["humidite_min"]:
                self._log("WARN",
                          f"[ALERTE] {p['nom']} : Humidite trop basse ! "
                          f"({hum}% < {p['humidite_min']}%)")
            if isinstance(sol, (int, float)) and sol < p["eau_min"]:
                self._log("WARN",
                          f"[ALERTE] {p['nom']} : Sol trop sec ! "
                          f"({sol}% < {p['eau_min']}%)")

# ─── Application principale ───────────────────────────────
class App:
    def __init__(self):
        self.fen = tk.Tk()
        self.fen.title("Serre Connectee v1.0")
        self.fen.configure(bg=C["fond"])
        self.fen.geometry("980x750")
        self.fen.resizable(False, False)
        init_db()
        self.page = None
        self._connexion()

    def _connexion(self):
        if self.page: self.page.destroy()
        self.page = PageConnexion(self.fen, self._dashboard)
        self.page.pack(fill="both", expand=True)

    def _dashboard(self, uid, email):
        if self.page: self.page.destroy()
        self.page = PageDashboard(self.fen, uid, email, self._connexion)
        self.page.pack(fill="both", expand=True)

    def run(self):
        self.fen.mainloop()

if __name__ == "__main__":
    App().run()
