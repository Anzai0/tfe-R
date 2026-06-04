# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import pymysql
pymysql.install_as_MySQLdb()
import pyrebase

# ─── FIREBASE CONFIG ───
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

# ─── MARIADB ───
def get_db():
    return pymysql.connect(
        host="localhost", user="ravza",
        password="ravza", database="serre"
    )

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS capteurs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255), temperature FLOAT,
            humidite_air FLOAT, humidite_sol FLOAT,
            pluie BOOLEAN, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plantes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255), nom VARCHAR(100),
            temp_max FLOAT, humidite_min FLOAT, eau_min FLOAT
        )
    """)
    conn.commit(); cursor.close(); conn.close()

# ─── PALETTE ───
C = {
    "fond":       "#0a0f1e",
    "fond2":      "#0d1529",
    "carte":      "#111d35",
    "carte2":     "#162040",
    "carte3":     "#1a2650",
    "texte":      "#e8f4f8",
    "gris":       "#4a6fa5",
    "gris2":      "#2a3f6f",
    "vert":       "#00ff88",
    "vert2":      "#00cc6a",
    "rouge":      "#ff4757",
    "rouge2":     "#cc2233",
    "orange":     "#ffa502",
    "bleu":       "#1e90ff",
    "bleu2":      "#0066cc",
    "accent":     "#00d4aa",
    "accent2":    "#009977",
    "violet":     "#7c4dff",
    "titre":      "#00d4aa",
    "btn_texte":  "#0a0f1e",
}

# ─── UTILS ───
def entry_style(e, width=None):
    kw = dict(bg=C["carte2"], fg=C["texte"], insertbackground=C["accent"],
              relief="flat", bd=0, font=("Segoe UI", 11), highlightthickness=1,
              highlightbackground=C["gris2"], highlightcolor=C["accent"])
    if width: kw["width"] = width
    e.configure(**kw)

def btn_style(b, bg=None, fg=None, size=11):
    b.configure(bg=bg or C["accent"], fg=fg or C["btn_texte"],
                relief="flat", bd=0, font=("Segoe UI", size, "bold"),
                cursor="hand2", activebackground=C["accent2"],
                activeforeground=C["btn_texte"])

def label_titre(parent, text, size=11, color=None):
    return tk.Label(parent, text=text, font=("Segoe UI", size, "bold"),
                    bg=parent.cget("bg"), fg=color or C["accent"])

def label_sub(parent, text, size=9, color=None):
    return tk.Label(parent, text=text, font=("Segoe UI", size),
                    bg=parent.cget("bg"), fg=color or C["gris"])

def separateur(parent, color=None):
    tk.Frame(parent, bg=color or C["gris2"], height=1).pack(fill="x", pady=8)

# ══════════════════════════════════════════
# PAGE CONNEXION
# ══════════════════════════════════════════
class PageConnexion(tk.Frame):
    def __init__(self, parent, on_connexion):
        super().__init__(parent, bg=C["fond"])
        self.on_connexion = on_connexion
        self._build()

    def _build(self):
        # ── Fond gauche décoratif ──
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        wrapper = tk.Frame(self, bg=C["fond"])
        wrapper.place(relx=0.5, rely=0.5, anchor="center", width=420)

        # Logo + titre
        logo_frame = tk.Frame(wrapper, bg=C["fond"])
        logo_frame.pack(pady=(0, 30))

        tk.Label(logo_frame, text="🌿", font=("Segoe UI", 56),
                 bg=C["fond"], fg=C["accent"]).pack()

        tk.Label(logo_frame, text="SERRE CONNECTÉE",
                 font=("Segoe UI", 22, "bold"),
                 bg=C["fond"], fg=C["titre"]).pack()

        tk.Label(logo_frame, text="Système intelligent de gestion",
                 font=("Segoe UI", 10),
                 bg=C["fond"], fg=C["gris"]).pack(pady=(4, 0))

        # Carte formulaire
        card = tk.Frame(wrapper, bg=C["carte"], pady=30, padx=35)
        card.pack(fill="x")

        # Onglets connexion / inscription
        tab_frame = tk.Frame(card, bg=C["carte2"], pady=4, padx=4)
        tab_frame.pack(fill="x", pady=(0, 25))

        self.btn_conn = tk.Button(tab_frame, text="CONNEXION",
                                   command=lambda: self._mode("connexion"),
                                   pady=7, padx=20, relief="flat",
                                   font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.btn_insc = tk.Button(tab_frame, text="INSCRIPTION",
                                   command=lambda: self._mode("inscription"),
                                   pady=7, padx=20, relief="flat",
                                   font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.btn_conn.pack(side="left", fill="x", expand=True)
        self.btn_insc.pack(side="left", fill="x", expand=True)

        self.mode_var = "connexion"
        self._mode("connexion")

        # Champs
        for label, attr, show in [
            ("📧  EMAIL", "entry_email", ""),
            ("🔒  MOT DE PASSE", "entry_mdp", "•")
        ]:
            tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                     bg=C["carte"], fg=C["gris"]).pack(anchor="w")
            e = tk.Entry(card, show=show)
            entry_style(e)
            e.pack(fill="x", pady=(4, 14), ipady=9)
            setattr(self, attr, e)

        # Bouton action
        self.btn_action = tk.Button(card, text="SE CONNECTER",
                                     command=self._action, pady=12)
        btn_style(self.btn_action, size=12)
        self.btn_action.pack(fill="x")

        # Message
        self.lbl_msg = tk.Label(card, text="", font=("Segoe UI", 9),
                                 bg=C["carte"], fg=C["rouge"])
        self.lbl_msg.pack(pady=(10, 0))

        # Footer
        tk.Label(wrapper, text="v1.0 • Serre IoT Project",
                 font=("Segoe UI", 8), bg=C["fond"], fg=C["gris2"]).pack(pady=(15, 0))

    def _mode(self, mode):
        self.mode_var = mode
        if mode == "connexion":
            self.btn_conn.configure(bg=C["accent"], fg=C["btn_texte"])
            self.btn_insc.configure(bg=C["carte2"], fg=C["gris"])
            if hasattr(self, "btn_action"):
                self.btn_action.configure(text="SE CONNECTER")
        else:
            self.btn_insc.configure(bg=C["accent"], fg=C["btn_texte"])
            self.btn_conn.configure(bg=C["carte2"], fg=C["gris"])
            if hasattr(self, "btn_action"):
                self.btn_action.configure(text="CRÉER UN COMPTE")

    def _action(self):
        email = self.entry_email.get().strip()
        mdp   = self.entry_mdp.get().strip()
        if not email or not mdp:
            self.lbl_msg.configure(text="⚠  Remplissez tous les champs")
            return

        txt = "SE CONNECTER" if self.mode_var == "connexion" else "CRÉER UN COMPTE"
        self.btn_action.configure(text="Chargement...", state="disabled")
        self.lbl_msg.configure(text="")

        def tache():
            try:
                if self.mode_var == "connexion":
                    user = auth.sign_in_with_email_and_password(email, mdp)
                else:
                    user = auth.create_user_with_email_and_password(email, mdp)
                uid = user["localId"]
                self.after(0, lambda: self.on_connexion(uid, email))
            except Exception as e:
                s = str(e)
                msg = "Email ou mot de passe incorrect"
                if "EMAIL_EXISTS"    in s: msg = "⚠  Email déjà utilisé"
                elif "WEAK_PASSWORD" in s: msg = "⚠  Mot de passe trop court (6 min)"
                elif "INVALID_EMAIL" in s: msg = "⚠  Email invalide"
                self.after(0, lambda: self.lbl_msg.configure(text=msg))
                self.after(0, lambda: self.btn_action.configure(text=txt, state="normal"))

        threading.Thread(target=tache, daemon=True).start()


# ══════════════════════════════════════════
# PAGE DASHBOARD
# ══════════════════════════════════════════
class PageDashboard(tk.Frame):
    def __init__(self, parent, uid, email, on_deconn):
        super().__init__(parent, bg=C["fond"])
        self.uid          = uid
        self.email        = email
        self.on_deconn    = on_deconn
        self.plantes      = []
        self.plante_active= None
        self.pompe_active = False
        self.ventilo_actif= False

        self._charger_plantes()
        self._build()
        self._rafraichir()

    # ── DB ──────────────────────────────────
    def _charger_plantes(self):
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("SELECT nom,temp_max,humidite_min,eau_min FROM plantes WHERE uid=%s", (self.uid,))
            self.plantes = [{"nom":r[0],"temp_max":r[1],"humidite_min":r[2],"eau_min":r[3]} for r in cur.fetchall()]
            cur.close(); conn.close()
        except: self.plantes = []
        if self.plantes: self.plante_active = self.plantes[0]

    # ── BUILD ────────────────────────────────
    def _build(self):
        # HEADER
        hdr = tk.Frame(self, bg=C["carte"], padx=20, pady=14)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=C["carte"])
        left.pack(side="left")
        tk.Label(left, text="🌿", font=("Segoe UI", 18),
                 bg=C["carte"], fg=C["accent"]).pack(side="left")
        tk.Label(left, text=" SERRE CONNECTÉE",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["carte"], fg=C["titre"]).pack(side="left")

        right = tk.Frame(hdr, bg=C["carte"])
        right.pack(side="right")

        tk.Label(right, text=f"👤  {self.email}",
                 font=("Segoe UI", 9), bg=C["carte"], fg=C["gris"]).pack(side="left", padx=15)

        btn_dc = tk.Button(right, text="⏻  DÉCONNEXION",
                            command=self.on_deconn, pady=6, padx=12)
        btn_style(btn_dc, bg=C["rouge"], fg=C["texte"])
        btn_dc.pack(side="left")

        # Barre de statut colorée
        self.barre = tk.Frame(self, bg=C["accent"], height=2)
        self.barre.pack(fill="x")

        # SCROLL AREA
        wrap = tk.Frame(self, bg=C["fond"])
        wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrap, bg=C["fond"], highlightthickness=0)
        sb     = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=C["fond"])

        self.inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._section_capteurs()
        self._section_actionneurs()
        self._section_plantes()

        self.lbl_statut = tk.Label(self.inner, text="",
                                    font=("Segoe UI", 8),
                                    bg=C["fond"], fg=C["gris"])
        self.lbl_statut.pack(pady=(5, 15))

    # ── SECTION CAPTEURS ────────────────────
    def _section_capteurs(self):
        outer = self._card(self.inner, titre="📡  DONNÉES EN TEMPS RÉEL")

        grille = tk.Frame(outer, bg=C["carte"])
        grille.pack(fill="x", pady=(5, 0))

        capteurs = [
            ("🌡", "Température",   "--°C",  "temp"),
            ("💧", "Humidité air",  "--%",   "hum"),
            ("🌱", "Humidité sol",  "--%",   "sol"),
            ("🌧", "Pluie",         "--",    "pluie"),
        ]
        self._vals = {}
        for i, (ico, nom, val, key) in enumerate(capteurs):
            c = tk.Frame(grille, bg=C["carte2"], padx=14, pady=12)
            c.grid(row=i//2, column=i%2, padx=6, pady=6, sticky="ew")
            grille.columnconfigure(i%2, weight=1)

            top = tk.Frame(c, bg=C["carte2"])
            top.pack(fill="x")
            tk.Label(top, text=ico, font=("Segoe UI", 14),
                     bg=C["carte2"], fg=C["gris"]).pack(side="left")
            tk.Label(top, text=f"  {nom}", font=("Segoe UI", 9),
                     bg=C["carte2"], fg=C["gris"]).pack(side="left")

            lbl = tk.Label(c, text=val, font=("Segoe UI", 22, "bold"),
                           bg=C["carte2"], fg=C["texte"])
            lbl.pack(anchor="w", pady=(4, 0))

            # Barre de progression sous la valeur
            bar_bg = tk.Frame(c, bg=C["gris2"], height=3)
            bar_bg.pack(fill="x", pady=(6, 0))
            bar_fill = tk.Frame(bar_bg, bg=C["accent"], height=3, width=0)
            bar_fill.place(x=0, y=0, relheight=1, relwidth=0.5)

            self._vals[key] = (lbl, bar_fill)

    # ── SECTION ACTIONNEURS ─────────────────
    def _section_actionneurs(self):
        outer = self._card(self.inner, titre="⚡  CONTRÔLE DES ACTIONNEURS")

        grille = tk.Frame(outer, bg=C["carte"])
        grille.pack(fill="x", pady=(5, 0))

        for col, (nom, ico, toggle_fn, state_attr, lbl_attr, btn_attr) in enumerate([
            ("POMPE",       "💧", self._toggle_pompe,   "pompe_active",  "lbl_pompe",  "btn_pompe"),
            ("VENTILATEUR", "🌀", self._toggle_ventilo, "ventilo_actif", "lbl_ventilo","btn_ventilo"),
        ]):
            c = tk.Frame(grille, bg=C["carte2"], padx=16, pady=16)
            c.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
            grille.columnconfigure(col, weight=1)

            tk.Label(c, text=ico, font=("Segoe UI", 26),
                     bg=C["carte2"], fg=C["gris"]).pack()
            tk.Label(c, text=nom, font=("Segoe UI", 9, "bold"),
                     bg=C["carte2"], fg=C["gris"]).pack()

            lbl = tk.Label(c, text="● OFF", font=("Segoe UI", 14, "bold"),
                           bg=C["carte2"], fg=C["rouge"])
            lbl.pack(pady=8)

            btn = tk.Button(c, text="ACTIVER", command=toggle_fn, pady=8)
            btn_style(btn)
            btn.pack(fill="x")

            setattr(self, lbl_attr, lbl)
            setattr(self, btn_attr, btn)

    # ── SECTION PLANTES ─────────────────────
    def _section_plantes(self):
        outer = self._card(self.inner, titre=f"🌱  MES PLANTES  ({len(self.plantes)}/3)")
        self._outer_plantes = outer
        self._outer_frame   = outer.master  # le card wrapper

        # Bouton ajouter
        if len(self.plantes) < 3:
            btn_add = tk.Button(outer, text="＋  AJOUTER UNE PLANTE",
                                 command=self._popup_plante, pady=7)
            btn_style(btn_add)
            btn_add.pack(fill="x", pady=(0, 12))
        else:
            tk.Label(outer, text="Maximum 3 plantes atteint",
                     font=("Segoe UI", 9), bg=C["carte"],
                     fg=C["orange"]).pack(anchor="w", pady=(0, 10))

        self.frame_liste = tk.Frame(outer, bg=C["carte"])
        self.frame_liste.pack(fill="x")
        self._afficher_plantes()

    def _afficher_plantes(self):
        for w in self.frame_liste.winfo_children():
            w.destroy()

        if not self.plantes:
            tk.Label(self.frame_liste,
                     text="Aucune plante — cliquez sur AJOUTER",
                     font=("Segoe UI", 10, "italic"),
                     bg=C["carte"], fg=C["gris"]).pack(pady=15)
            return

        for plante in self.plantes:
            actif = self.plante_active and self.plante_active["nom"] == plante["nom"]
            border_color = C["accent"] if actif else C["gris2"]

            c = tk.Frame(self.frame_liste, bg=border_color, pady=1, padx=1)
            c.pack(fill="x", pady=5)
            inner = tk.Frame(c, bg=C["carte3"] if actif else C["carte2"], padx=14, pady=12)
            inner.pack(fill="x")

            top = tk.Frame(inner, bg=inner.cget("bg"))
            top.pack(fill="x")

            tk.Label(top, text=f"🌿  {plante['nom']}",
                     font=("Segoe UI", 12, "bold"),
                     bg=inner.cget("bg"),
                     fg=C["accent"] if actif else C["texte"]).pack(side="left")

            if actif:
                tk.Label(top, text="  ✓ ACTIVE",
                         font=("Segoe UI", 8, "bold"),
                         bg=inner.cget("bg"), fg=C["vert"]).pack(side="left")

            # Infos
            info_frame = tk.Frame(inner, bg=inner.cget("bg"))
            info_frame.pack(fill="x", pady=(8, 0))

            for ico, label, val, unit in [
                ("🌡", "Temp max",   plante["temp_max"],     "°C"),
                ("💧", "Hum min",    plante["humidite_min"], "%"),
                ("🚿", "Eau min",    plante["eau_min"],      "%"),
            ]:
                chip = tk.Frame(info_frame, bg=C["gris2"], padx=8, pady=4)
                chip.pack(side="left", padx=(0, 6))
                tk.Label(chip, text=f"{ico} {label}: {val}{unit}",
                         font=("Segoe UI", 8), bg=C["gris2"],
                         fg=C["texte"]).pack()

            # Boutons
            btn_frame = tk.Frame(inner, bg=inner.cget("bg"))
            btn_frame.pack(fill="x", pady=(10, 0))

            if not actif:
                b_sel = tk.Button(btn_frame, text="SÉLECTIONNER",
                                   command=lambda p=plante: self._selectionner(p),
                                   pady=5, padx=10)
                btn_style(b_sel)
                b_sel.pack(side="left")

            b_sup = tk.Button(btn_frame, text="🗑  SUPPRIMER",
                               command=lambda p=plante: self._supprimer(p),
                               pady=5, padx=10)
            btn_style(b_sup, bg=C["rouge"], fg=C["texte"])
            b_sup.pack(side="right")

    # ── POPUP AJOUT PLANTE ──────────────────
    def _popup_plante(self):
        if len(self.plantes) >= 3:
            messagebox.showwarning("Limite atteinte", "Maximum 3 plantes autorisées !")
            return

        pop = tk.Toplevel(self)
        pop.title("Nouvelle plante")
        pop.configure(bg=C["fond"])
        pop.geometry("420x480")
        pop.resizable(False, False)
        pop.grab_set()

        tk.Label(pop, text="🌱  NOUVELLE PLANTE",
                 font=("Segoe UI", 15, "bold"),
                 bg=C["fond"], fg=C["accent"]).pack(pady=(25, 5))
        tk.Label(pop, text="Configurez les seuils de votre plante",
                 font=("Segoe UI", 9), bg=C["fond"], fg=C["gris"]).pack()

        card = tk.Frame(pop, bg=C["carte"], padx=30, pady=25)
        card.pack(fill="x", padx=25, pady=20)

        champs = [
            ("🌿  NOM DE LA PLANTE",    "nom",          ""),
            ("🌡  TEMPÉRATURE MAX (°C)", "temp_max",     "30"),
            ("💧  HUMIDITÉ MINI (%)",    "humidite_min", "50"),
            ("🚿  EAU MINI (%)",         "eau_min",      "30"),
        ]
        entries = {}
        for label, key, default in champs:
            tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                     bg=C["carte"], fg=C["gris"]).pack(anchor="w")
            e = tk.Entry(card)
            entry_style(e)
            e.insert(0, default)
            e.pack(fill="x", pady=(4, 12), ipady=8)
            entries[key] = e

        lbl_err = tk.Label(card, text="", font=("Segoe UI", 9),
                            bg=C["carte"], fg=C["rouge"])
        lbl_err.pack()

        def sauvegarder():
            nom = entries["nom"].get().strip()
            if not nom:
                lbl_err.configure(text="⚠  Le nom est obligatoire"); return
            if any(p["nom"].lower() == nom.lower() for p in self.plantes):
                lbl_err.configure(text="⚠  Cette plante existe déjà"); return
            try:
                tm = float(entries["temp_max"].get())
                hm = float(entries["humidite_min"].get())
                em = float(entries["eau_min"].get())
            except:
                lbl_err.configure(text="⚠  Valeurs numériques invalides"); return
            try:
                conn = get_db(); cur = conn.cursor()
                cur.execute(
                    "INSERT INTO plantes (uid,nom,temp_max,humidite_min,eau_min) VALUES (%s,%s,%s,%s,%s)",
                    (self.uid, nom, tm, hm, em))
                conn.commit(); cur.close(); conn.close()
            except Exception as e:
                lbl_err.configure(text=f"⚠  Erreur DB: {e}"); return

            self.plantes.append({"nom": nom, "temp_max": tm, "humidite_min": hm, "eau_min": em})
            if not self.plante_active: self.plante_active = self.plantes[0]
            self._rebuild_plantes()
            pop.destroy()

        btn = tk.Button(card, text="✓  AJOUTER LA PLANTE",
                         command=sauvegarder, pady=11)
        btn_style(btn, size=11)
        btn.pack(fill="x", pady=(8, 0))

    def _rebuild_plantes(self):
        # Reconstruit uniquement la section plantes
        for w in self.inner.winfo_children():
            if hasattr(w, "_is_plante_section"):
                w.destroy()
        # Plus simple : reconstruire tout le contenu
        for w in self.inner.winfo_children():
            w.destroy()
        self._section_capteurs()
        self._section_actionneurs()
        self._section_plantes()
        self.lbl_statut = tk.Label(self.inner, text="",
                                    font=("Segoe UI", 8),
                                    bg=C["fond"], fg=C["gris"])
        self.lbl_statut.pack(pady=(5, 15))

    # ── ACTIONS ─────────────────────────────
    def _selectionner(self, plante):
        self.plante_active = plante
        self._afficher_plantes()

    def _supprimer(self, plante):
        if not messagebox.askyesno("Supprimer", f"Supprimer « {plante['nom']} » ?"):
            return
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("DELETE FROM plantes WHERE uid=%s AND nom=%s", (self.uid, plante["nom"]))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            print(f"Erreur: {e}")
        self.plantes = [p for p in self.plantes if p["nom"] != plante["nom"]]
        if self.plante_active and self.plante_active["nom"] == plante["nom"]:
            self.plante_active = self.plantes[0] if self.plantes else None
        self._rebuild_plantes()

    def _toggle_pompe(self):
        self.pompe_active = not self.pompe_active
        if self.pompe_active:
            self.lbl_pompe.configure(text="● ON", fg=C["vert"])
            self.btn_pompe.configure(text="DÉSACTIVER", bg=C["rouge"])
        else:
            self.lbl_pompe.configure(text="● OFF", fg=C["rouge"])
            self.btn_pompe.configure(text="ACTIVER", bg=C["accent"])
        self._cmd("pompe", self.pompe_active)

    def _toggle_ventilo(self):
        self.ventilo_actif = not self.ventilo_actif
        if self.ventilo_actif:
            self.lbl_ventilo.configure(text="● ON", fg=C["vert"])
            self.btn_ventilo.configure(text="DÉSACTIVER", bg=C["rouge"])
        else:
            self.lbl_ventilo.configure(text="● OFF", fg=C["rouge"])
            self.btn_ventilo.configure(text="ACTIVER", bg=C["accent"])
        self._cmd("ventilateur", self.ventilo_actif)

    def _cmd(self, appareil, etat):
        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update({appareil: etat}),
            daemon=True).start()

    # ── CAPTEURS ────────────────────────────
    def _rafraichir(self):
        def tache():
            try:
                d = db.child("capteurs").child(self.uid).get().val()
                if d:
                    self.after(0, self._update, d)
                    self._save_db(d)
            except Exception as e:
                print(f"Firebase: {e}")
            self.after(5000, self._rafraichir)
        threading.Thread(target=tache, daemon=True).start()

    def _save_db(self, d):
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute(
                "INSERT INTO capteurs (uid,temperature,humidite_air,humidite_sol,pluie) VALUES (%s,%s,%s,%s,%s)",
                (self.uid, d.get("temperature"), d.get("humidite_air"), d.get("humidite_sol"), d.get("pluie", False)))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            print(f"MariaDB: {e}")

    def _update(self, d):
        temp  = d.get("temperature", "--")
        hum   = d.get("humidite_air", "--")
        sol   = d.get("humidite_sol", "--")
        pluie = d.get("pluie", False)

        configs = {
            "temp":  (f"{temp}°C",  C["rouge"] if isinstance(temp, (int,float)) and temp > 30 else C["vert"], 0.7),
            "hum":   (f"{hum}%",    C["orange"] if isinstance(hum,(int,float)) and hum < 40 else C["vert"], hum/100 if isinstance(hum,(int,float)) else 0.5),
            "sol":   (f"{sol}%",    C["rouge"] if isinstance(sol,(int,float)) and sol < 30 else C["vert"], sol/100 if isinstance(sol,(int,float)) else 0.5),
            "pluie": ("OUI 🌧" if pluie else "NON ☀",  C["bleu"] if pluie else C["gris"], 1.0 if pluie else 0.1),
        }
        for key, (txt, color, ratio) in configs.items():
            lbl, bar = self._vals[key]
            lbl.configure(text=txt, fg=color)
            bar.configure(bg=color)
            bar.place(relwidth=min(max(ratio, 0), 1))

        self.lbl_statut.configure(
            text=f"🕐  Dernière mise à jour : {time.strftime('%H:%M:%S')}",
            fg=C["gris"])

    # ── HELPER ──────────────────────────────
    def _card(self, parent, titre=""):
        wrapper = tk.Frame(parent, bg=C["accent"], pady=1, padx=1)
        wrapper.pack(fill="x", padx=15, pady=8)

        card = tk.Frame(wrapper, bg=C["carte"], padx=20, pady=16)
        card.pack(fill="x")

        if titre:
            tk.Label(card, text=titre, font=("Segoe UI", 11, "bold"),
                     bg=C["carte"], fg=C["accent"]).pack(anchor="w", pady=(0, 8))
            tk.Frame(card, bg=C["gris2"], height=1).pack(fill="x", pady=(0, 10))

        return card


# ══════════════════════════════════════════
# APP
# ══════════════════════════════════════════
class App:
    def __init__(self):
        self.fen = tk.Tk()
        self.fen.title("Serre Connectée")
        self.fen.configure(bg=C["fond"])
        self.fen.geometry("700x800")
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

    def lancer(self):
        self.fen.mainloop()

if __name__ == "__main__":
    App().lancer()
