# -*- coding: utf-8 -*-
# interface graphique de la serre connectee
# permet de voir les capteurs et controler la pompe et le ventilateur

import tkinter as tk
from tkinter import messagebox
import threading
import time
import pymysql
pymysql.install_as_MySQLdb()
import pyrebase

# connexion firebase
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

# couleurs de l'interface
FOND = "#0a0f1e"
FOND2 = "#0d1529"
CARTE = "#111d35"
CARTE2 = "#162040"
CARTE3 = "#1a2650"
TEXTE = "#e8f4f8"
GRIS = "#4a6fa5"
GRIS2 = "#1e2d50"
VERT = "#00ff88"
VERT2 = "#00cc6a"
ROUGE = "#ff4757"
ORANGE = "#ffa502"
BLEU = "#1e90ff"
ACCENT = "#00d4aa"
ACCENT2 = "#009977"
TITRE = "#00d4aa"
CONSOLE = "#050d1a"

# connexion a la base de donnees mysql
def get_db():
    return pymysql.connect(
        host="localhost",
        user="ravza",
        password="ravza",
        database="serre",
        charset="utf8mb4"
    )

# je cree les tables si elles existent pas encore
def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capteurs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                uid VARCHAR(255),
                temperature FLOAT,
                humidite_air FLOAT,
                humidite_sol FLOAT,
                pluie BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS plantes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                uid VARCHAR(255),
                nom VARCHAR(100),
                temp_max FLOAT,
                humidite_min FLOAT,
                eau_min FLOAT
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("[DB] Erreur init: " + str(e))

# style pour les boutons
def style_bouton(bouton, bg=ACCENT, fg=FOND, taille=10):
    bouton.configure(
        bg=bg,
        fg=fg,
        font=("Courier", taille, "bold"),
        relief="flat",
        bd=0,
        cursor="hand2",
        activebackground=ACCENT2,
        activeforeground=FOND
    )

# style pour les champs de texte
def style_entry(entry):
    entry.configure(
        bg=GRIS2,
        fg=TEXTE,
        font=("Courier", 10),
        relief="flat",
        bd=0,
        insertbackground=ACCENT,
        selectbackground=ACCENT
    )

# ---- page de connexion ----
class PageConnexion(tk.Frame):
    def __init__(self, parent, quand_connecte):
        super().__init__(parent, bg=FOND)
        self.quand_connecte = quand_connecte
        self.mode = "connexion"  # ou "inscription"
        self.construire()

    def construire(self):
        # je centre tout au milieu de la fenetre
        wrap = tk.Frame(self, bg=FOND)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrap, text="◈ SERRE CONNECTEE",
                 font=("Courier", 22, "bold"),
                 bg=FOND, fg=ACCENT).pack(pady=(0, 4))

        tk.Label(wrap, text="Systeme de monitoring IoT",
                 font=("Courier", 10),
                 bg=FOND, fg=GRIS).pack()

        tk.Frame(wrap, bg=ACCENT, height=2).pack(fill="x", pady=(16, 20))

        # la carte avec le formulaire
        card = tk.Frame(wrap, bg=CARTE, padx=30, pady=30)
        card.pack(ipadx=10, ipady=10)

        self.lbl_titre = tk.Label(card, text="[ SE CONNECTER ]",
                                   font=("Courier", 13, "bold"),
                                   bg=CARTE, fg=ACCENT)
        self.lbl_titre.pack(pady=(0, 20))

        tk.Label(card, text="Email", font=("Courier", 9),
                 bg=CARTE, fg=GRIS).pack(anchor="w")
        self.e_email = tk.Entry(card, width=30)
        style_entry(self.e_email)
        self.e_email.pack(fill="x", pady=(2, 12), ipady=6)

        tk.Label(card, text="Mot de passe", font=("Courier", 9),
                 bg=CARTE, fg=GRIS).pack(anchor="w")
        self.e_mdp = tk.Entry(card, width=30, show="*")
        style_entry(self.e_mdp)
        self.e_mdp.pack(fill="x", pady=(2, 16), ipady=6)

        self.lbl_msg = tk.Label(card, text="",
                                 font=("Courier", 9),
                                 bg=CARTE, fg=ROUGE)
        self.lbl_msg.pack()

        self.btn_ok = tk.Button(card, text="[ SE CONNECTER ]",
                                 command=self.action, pady=8)
        style_bouton(self.btn_ok)
        self.btn_ok.pack(fill="x", pady=(8, 12))

        self.btn_switch = tk.Button(card,
                                     text="Pas de compte ? Creer un compte",
                                     command=self.changer_mode,
                                     bg=CARTE, fg=GRIS,
                                     font=("Courier", 8),
                                     relief="flat", bd=0, cursor="hand2")
        self.btn_switch.pack()

    # je change entre connexion et inscription
    def changer_mode(self):
        if self.mode == "connexion":
            self.mode = "inscription"
            self.lbl_titre.configure(text="[ CREER UN COMPTE ]")
            self.btn_ok.configure(text="[ CREER UN COMPTE ]")
            self.btn_switch.configure(text="Deja un compte ? Se connecter")
        else:
            self.mode = "connexion"
            self.lbl_titre.configure(text="[ SE CONNECTER ]")
            self.btn_ok.configure(text="[ SE CONNECTER ]")
            self.btn_switch.configure(text="Pas de compte ? Creer un compte")

    def action(self):
        email = self.e_email.get().strip()
        mdp = self.e_mdp.get().strip()

        if not email or not mdp:
            self.lbl_msg.configure(text="[!] Remplissez tous les champs")
            return

        self.btn_ok.configure(text="...", state="disabled")
        self.lbl_msg.configure(text="")

        # je fais la connexion dans un thread pour pas bloquer l'interface
        def essayer():
            try:
                if self.mode == "connexion":
                    user = auth.sign_in_with_email_and_password(email, mdp)
                else:
                    user = auth.create_user_with_email_and_password(email, mdp)
                uid = user["localId"]
                self.after(0, lambda: self.quand_connecte(uid, email))
            except Exception as e:
                msg = "[!] Email ou mot de passe incorrect"
                if "EMAIL_EXISTS" in str(e):
                    msg = "[!] Cet email existe deja"
                self.after(0, lambda: self.lbl_msg.configure(text=msg))
                self.after(0, lambda: self.btn_ok.configure(
                    text="[ SE CONNECTER ]" if self.mode == "connexion"
                    else "[ CREER UN COMPTE ]",
                    state="normal"))

        threading.Thread(target=essayer, daemon=True).start()


# ---- page principale (dashboard) ----
class PageDashboard(tk.Frame):
    def __init__(self, parent, uid, email, quand_deconnecte):
        super().__init__(parent, bg=FOND)
        self.uid = uid
        self.email = email
        self.quand_deconnecte = quand_deconnecte

        # variables d'etat
        self.pompe_on = False
        self.ventilo_on = False
        self.mode_auto = False
        self.plantes = []
        self.plante_active = None

        # je stocke les labels et barres des capteurs ici
        self._vals = {}

        self.construire()
        self.charger_plantes()
        self.log("INFO", "Systeme demarre")
        self.log("INFO", "User: " + self.email)
        self.log("INFO", "UID : " + self.uid[:12] + "...")
        self.log("INFO", "En attente des capteurs...")
        self.rafraichir()

    def construire(self):
        # barre du haut
        header = tk.Frame(self, bg=FOND2, pady=10)
        header.pack(fill="x", padx=0)

        tk.Label(header, text="◈ SERRE CONNECTEE",
                 font=("Courier", 16, "bold"),
                 bg=FOND2, fg=ACCENT).pack(side="left", padx=16)

        tk.Label(header, text=self.email,
                 font=("Courier", 9),
                 bg=FOND2, fg=GRIS).pack(side="left", padx=8)

        btn_deco = tk.Button(header, text="[ DECONNEXION ]",
                              command=self.deconnexion, pady=4, padx=10)
        style_bouton(btn_deco, bg=ROUGE, fg=TEXTE)
        btn_deco.pack(side="right", padx=16)

        # le corps avec colonne gauche et colonne droite
        corps = tk.Frame(self, bg=FOND)
        corps.pack(fill="both", expand=True, padx=12, pady=12)

        # colonne gauche avec scroll
        left_wrap = tk.Frame(corps, bg=FOND)
        left_wrap.pack(side="left", fill="both", expand=True)

        canvas = tk.Canvas(left_wrap, bg=FOND, highlightthickness=0)
        sb = tk.Scrollbar(left_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(canvas, bg=FOND)
        win_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        self.inner.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        # je construis les sections
        self.section_capteurs()
        self.section_actionneurs()
        self.section_plantes()

        self.lbl_statut = tk.Label(self.inner, text="",
                                    font=("Courier", 8),
                                    bg=FOND, fg=GRIS)
        self.lbl_statut.pack(pady=5)

        # colonne droite : la console de logs
        right = tk.Frame(corps, bg=FOND, width=300)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        tk.Label(right, text=">> CONSOLE",
                 font=("Courier", 10, "bold"),
                 bg=FOND, fg=ACCENT).pack(anchor="w", pady=(0, 6))

        self.console = tk.Text(right, bg=CONSOLE, fg=TEXTE,
                                font=("Courier", 8),
                                state="disabled", wrap="word",
                                relief="flat", bd=0)
        self.console.pack(fill="both", expand=True)

        # couleurs dans la console
        self.console.tag_configure("TIME", foreground=GRIS)
        self.console.tag_configure("INFO", foreground=ACCENT)
        self.console.tag_configure("WARN", foreground=ORANGE)
        self.console.tag_configure("ERROR", foreground=ROUGE)
        self.console.tag_configure("OK", foreground=VERT)
        self.console.tag_configure("DATA", foreground=BLEU)

        btn_clear = tk.Button(right, text="[ VIDER ]",
                               command=self.vider_console, pady=4)
        style_bouton(btn_clear, bg=GRIS2, fg=TEXTE, taille=8)
        btn_clear.pack(fill="x", pady=(6, 0))

    # je cree une carte avec un titre
    def creer_carte(self, parent, titre):
        tk.Label(parent, text=titre,
                 font=("Courier", 11, "bold"),
                 bg=FOND, fg=TITRE).pack(anchor="w", pady=(12, 4))
        card = tk.Frame(parent, bg=CARTE, padx=16, pady=14)
        card.pack(fill="x", pady=(0, 6))
        return card

    # section des capteurs
    def section_capteurs(self):
        card = self.creer_carte(self.inner, ">> CAPTEURS")

        capteurs_infos = [
            ("temp",  "TEMPERATURE",  "C"),
            ("hum",   "HUMIDITE AIR", "%"),
            ("sol",   "HUMIDITE SOL", "%"),
            ("pluie", "PLUIE",        ""),
        ]

        for key, label, unite in capteurs_infos:
            ligne = tk.Frame(card, bg=CARTE)
            ligne.pack(fill="x", pady=6)

            tk.Label(ligne, text=label,
                     font=("Courier", 9),
                     bg=CARTE, fg=GRIS,
                     width=16, anchor="w").pack(side="left")

            lbl_val = tk.Label(ligne, text="--",
                                font=("Courier", 12, "bold"),
                                bg=CARTE, fg=TEXTE,
                                width=8, anchor="w")
            lbl_val.pack(side="left")

            # barre de progression
            barre_fond = tk.Frame(ligne, bg=GRIS2, height=6)
            barre_fond.pack(side="left", fill="x", expand=True, padx=(8, 0))
            barre_fond.pack_propagate(False)

            barre = tk.Frame(barre_fond, bg=VERT, height=6)
            barre.place(relwidth=0, relheight=1)

            self._vals[key] = (lbl_val, barre)

    # section pompe et ventilateur
    def section_actionneurs(self):
        card = self.creer_carte(self.inner, ">> ACTIONNEURS")

        # ligne du mode auto
        ligne_auto = tk.Frame(card, bg=CARTE)
        ligne_auto.pack(fill="x", pady=(0, 12))

        tk.Label(ligne_auto, text="MODE AUTO :",
                 font=("Courier", 10, "bold"),
                 bg=CARTE, fg=ACCENT).pack(side="left")

        self.lbl_auto = tk.Label(ligne_auto, text="[OFF]",
                                  font=("Courier", 10, "bold"),
                                  bg=CARTE, fg=ROUGE)
        self.lbl_auto.pack(side="left", padx=10)

        self.btn_auto = tk.Button(ligne_auto, text="[ACTIVER AUTO]",
                                   command=self.toggle_auto, pady=5, padx=10)
        style_bouton(self.btn_auto)
        self.btn_auto.pack(side="right")

        tk.Frame(card, bg=GRIS2, height=1).pack(fill="x", pady=(0, 10))

        # pompe et ventilo cote a cote
        grille = tk.Frame(card, bg=CARTE)
        grille.pack(fill="x")

        # --- pompe ---
        col_pompe = tk.Frame(grille, bg=CARTE2, padx=12, pady=12)
        col_pompe.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(col_pompe, text="POMPE",
                 font=("Courier", 10, "bold"),
                 bg=CARTE2, fg=TEXTE).pack()

        self.lbl_pompe = tk.Label(col_pompe, text="[OFF]",
                                   font=("Courier", 14, "bold"),
                                   bg=CARTE2, fg=ROUGE)
        self.lbl_pompe.pack(pady=8)

        self.btn_pompe = tk.Button(col_pompe, text="[ACTIVER]",
                                    command=self.toggle_pompe, pady=6)
        style_bouton(self.btn_pompe)
        self.btn_pompe.pack(fill="x")

        # --- ventilateur ---
        col_ventilo = tk.Frame(grille, bg=CARTE2, padx=12, pady=12)
        col_ventilo.pack(side="left", fill="both", expand=True)

        tk.Label(col_ventilo, text="VENTILATEUR",
                 font=("Courier", 10, "bold"),
                 bg=CARTE2, fg=TEXTE).pack()

        self.lbl_ventilo = tk.Label(col_ventilo, text="[OFF]",
                                     font=("Courier", 14, "bold"),
                                     bg=CARTE2, fg=ROUGE)
        self.lbl_ventilo.pack(pady=8)

        self.btn_ventilo = tk.Button(col_ventilo, text="[ACTIVER]",
                                      command=self.toggle_ventilo, pady=6)
        style_bouton(self.btn_ventilo)
        self.btn_ventilo.pack(fill="x")

    # section plantes
    def section_plantes(self):
        self.afficher_plantes()

    def afficher_plantes(self):
        # je supprime et reaffiche la section plantes
        if hasattr(self, "_card_plantes") and self._card_plantes.winfo_exists():
            self._card_plantes.destroy()

        card = self.creer_carte(self.inner, ">> MES PLANTES")
        self._card_plantes = card

        btn_add = tk.Button(card, text="[+ AJOUTER UNE PLANTE]",
                             command=self.popup_plante, pady=7)
        style_bouton(btn_add)
        btn_add.pack(fill="x", pady=(0, 12))

        if not self.plantes:
            tk.Label(card, text="Aucune plante enregistree",
                     font=("Courier", 9),
                     bg=CARTE, fg=GRIS).pack()
            return

        for p in self.plantes:
            actif = self.plante_active and self.plante_active["nom"] == p["nom"]
            ibg = CARTE3 if actif else CARTE2

            inner = tk.Frame(card, bg=ibg, padx=12, pady=10)
            inner.pack(fill="x", pady=(0, 8))

            ligne_titre = tk.Frame(inner, bg=ibg)
            ligne_titre.pack(fill="x")

            ico = "★" if actif else "○"
            tk.Label(ligne_titre,
                     text=ico + " " + p["nom"].upper(),
                     font=("Courier", 11, "bold"),
                     bg=ibg,
                     fg=VERT if actif else TEXTE).pack(side="left")

            if actif:
                tk.Label(ligne_titre, text="[ ACTIVE ]",
                         font=("Courier", 8, "bold"),
                         bg=ibg, fg=VERT).pack(side="right")

            # infos de la plante
            infos = [
                ("Temp max", str(p["temp_max"]) + " C"),
                ("Humidite min", str(p["humidite_min"]) + " %"),
                ("Sol min", str(p["eau_min"]) + " %"),
            ]
            for label, val in infos:
                ligne_info = tk.Frame(inner, bg=ibg)
                ligne_info.pack(fill="x", pady=1)
                tk.Label(ligne_info, text=label + " :",
                         font=("Courier", 8),
                         bg=ibg, fg=GRIS,
                         width=14, anchor="w").pack(side="left")
                tk.Label(ligne_info, text=val,
                         font=("Courier", 8, "bold"),
                         bg=ibg, fg=TEXTE).pack(side="left")

            # boutons activer / supprimer
            ligne_btn = tk.Frame(inner, bg=ibg)
            ligne_btn.pack(fill="x", pady=(8, 0))

            if not actif:
                btn_activer = tk.Button(ligne_btn, text="[ACTIVER]",
                                         command=lambda pl=p: self.activer_plante(pl),
                                         pady=4, padx=8)
                style_bouton(btn_activer, taille=8)
                btn_activer.pack(side="left", padx=(0, 6))

            btn_suppr = tk.Button(ligne_btn, text="[SUPPRIMER]",
                                   command=lambda pl=p: self.supprimer_plante(pl),
                                   pady=4, padx=8)
            style_bouton(btn_suppr, bg=ROUGE, fg=TEXTE, taille=8)
            btn_suppr.pack(side="left")

    # je charge les plantes depuis mysql
    def charger_plantes(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT nom, temp_max, humidite_min, eau_min FROM plantes WHERE uid=%s", (self.uid,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self.plantes = [
                {"nom": r[0], "temp_max": r[1], "humidite_min": r[2], "eau_min": r[3]}
                for r in rows
            ]
            if self.plantes and not self.plante_active:
                self.plante_active = self.plantes[0]
        except Exception as e:
            self.log("ERROR", "Chargement plantes: " + str(e))

    # j'active une plante
    def activer_plante(self, plante):
        self.plante_active = plante
        self.log("OK", "Plante activee: " + plante["nom"])

        # j'envoie la plante active sur firebase
        def envoyer():
            try:
                db.child("commandes").child(self.uid).update({
                    "plante_active": plante
                })
            except Exception as e:
                self.log("ERROR", "Firebase plante: " + str(e))

        threading.Thread(target=envoyer, daemon=True).start()
        self.afficher_plantes()

    # je supprime une plante
    def supprimer_plante(self, plante):
        if not messagebox.askyesno("Supprimer", "Supprimer " + plante["nom"] + " ?"):
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM plantes WHERE uid=%s AND nom=%s",
                        (self.uid, plante["nom"]))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            self.log("ERROR", "Suppression: " + str(e))

        self.plantes = [x for x in self.plantes if x["nom"] != plante["nom"]]

        if self.plante_active and self.plante_active["nom"] == plante["nom"]:
            self.plante_active = self.plantes[0] if self.plantes else None
            if self.mode_auto and not self.plante_active:
                self.mode_auto = False
                self.log("WARN", "Auto desactive: plus de plante selectionnee")
                threading.Thread(
                    target=lambda: db.child("commandes").child(self.uid).update({"auto": False}),
                    daemon=True).start()

        self.afficher_plantes()
        self.log("WARN", "Plante supprimee: " + plante["nom"])

    # popup pour ajouter une plante
    def popup_plante(self):
        pop = tk.Toplevel(self)
        pop.title("Nouvelle plante")
        pop.configure(bg=FOND)
        pop.geometry("400x420")
        pop.resizable(False, False)

        card = tk.Frame(pop, bg=CARTE, padx=24, pady=24)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text="[ NOUVELLE PLANTE ]",
                 font=("Courier", 13, "bold"),
                 bg=CARTE, fg=ACCENT).pack(pady=(0, 16))

        entries = {}
        champs = [
            ("nom",          "Nom de la plante",       "ex: Tomate"),
            ("temp_max",     "Temperature max (C)",    "ex: 30"),
            ("humidite_min", "Humidite air min (%)",   "ex: 60"),
            ("eau_min",      "Humidite sol min (%)",   "ex: 35"),
        ]

        for key, label, placeholder in champs:
            tk.Label(card, text=label,
                     font=("Courier", 9),
                     bg=CARTE, fg=GRIS).pack(anchor="w")
            e = tk.Entry(card, width=30)
            style_entry(e)
            e.insert(0, placeholder)

            # je vide le champ quand on clique dessus
            def on_focus(event, ph=placeholder):
                if event.widget.get() == ph:
                    event.widget.delete(0, "end")

            e.bind("<FocusIn>", on_focus)
            e.pack(fill="x", pady=(2, 10), ipady=6)
            entries[key] = e

        lbl_err = tk.Label(card, text="",
                            font=("Courier", 9),
                            bg=CARTE, fg=ROUGE)
        lbl_err.pack()

        def sauvegarder():
            nom = entries["nom"].get().strip()
            try:
                temp_max = float(entries["temp_max"].get())
                hum_min = float(entries["humidite_min"].get())
                eau_min = float(entries["eau_min"].get())
            except:
                lbl_err.configure(text="[!] Valeurs incorrectes")
                return

            if not nom or nom == "ex: Tomate":
                lbl_err.configure(text="[!] Entrez un nom")
                return

            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO plantes (uid, nom, temp_max, humidite_min, eau_min) VALUES (%s,%s,%s,%s,%s)",
                    (self.uid, nom, temp_max, hum_min, eau_min)
                )
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                lbl_err.configure(text="[!] Erreur DB: " + str(e))
                return

            nouvelle = {"nom": nom, "temp_max": temp_max, "humidite_min": hum_min, "eau_min": eau_min}
            self.plantes.append(nouvelle)
            if not self.plante_active:
                self.plante_active = nouvelle
            self.afficher_plantes()
            self.log("OK", "Plante ajoutee: " + nom)
            pop.destroy()

        btn_ok = tk.Button(card, text="[ ENREGISTRER ]",
                            command=sauvegarder, pady=8)
        style_bouton(btn_ok)
        btn_ok.pack(fill="x", pady=(8, 0))

    # toggle mode automatique
    def toggle_auto(self):
        if not self.mode_auto and not self.plante_active:
            self.log("WARN", "Selectionnez une plante avant d'activer le mode auto")
            return

        self.mode_auto = not self.mode_auto

        if self.mode_auto:
            self.lbl_auto.configure(text="[ON]", fg=VERT)
            self.btn_auto.configure(text="[DESACTIVER AUTO]", bg=ROUGE, fg=TEXTE)
            self.btn_pompe.configure(state="disabled")
            self.btn_ventilo.configure(state="disabled")
            self.log("OK", "Mode automatique active")
        else:
            self.lbl_auto.configure(text="[OFF]", fg=ROUGE)
            self.btn_auto.configure(text="[ACTIVER AUTO]", bg=ACCENT, fg=FOND)
            self.btn_pompe.configure(state="normal")
            self.btn_ventilo.configure(state="normal")
            self.log("WARN", "Mode automatique desactive")

        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update({"auto": self.mode_auto}),
            daemon=True).start()

    # toggle pompe
    def toggle_pompe(self):
        if self.mode_auto:
            self.log("WARN", "Mode AUTO actif, controle manuel desactive")
            return

        self.pompe_on = not self.pompe_on

        if self.pompe_on:
            self.lbl_pompe.configure(text="[ON]", fg=VERT)
            self.btn_pompe.configure(text="[DESACTIVER]", bg=ROUGE, fg=TEXTE)
            self.log("OK", "Pompe activee manuellement")
        else:
            self.lbl_pompe.configure(text="[OFF]", fg=ROUGE)
            self.btn_pompe.configure(text="[ACTIVER]", bg=ACCENT, fg=FOND)
            self.log("WARN", "Pompe desactivee manuellement")

        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update({"pompe": self.pompe_on}),
            daemon=True).start()

    # toggle ventilateur
    def toggle_ventilo(self):
        if self.mode_auto:
            self.log("WARN", "Mode AUTO actif, controle manuel desactive")
            return

        self.ventilo_on = not self.ventilo_on

        if self.ventilo_on:
            self.lbl_ventilo.configure(text="[ON]", fg=VERT)
            self.btn_ventilo.configure(text="[DESACTIVER]", bg=ROUGE, fg=TEXTE)
            self.log("OK", "Ventilateur active manuellement")
        else:
            self.lbl_ventilo.configure(text="[OFF]", fg=ROUGE)
            self.btn_ventilo.configure(text="[ACTIVER]", bg=ACCENT, fg=FOND)
            self.log("WARN", "Ventilateur desactive manuellement")

        threading.Thread(
            target=lambda: db.child("commandes").child(self.uid).update({"ventilateur": self.ventilo_on}),
            daemon=True).start()

    # je mets un message dans la console
    def log(self, niveau, msg):
        self.console.configure(state="normal")
        t = time.strftime("%H:%M:%S")
        self.console.insert("end", "[" + t + "] ", "TIME")
        self.console.insert("end", "[" + niveau + "] " + msg + "\n", niveau)
        self.console.see("end")
        self.console.configure(state="disabled")

    def vider_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    # je lis les donnees firebase et je mets a jour l'interface
    def rafraichir(self):
        self.log("INFO", "Connexion Firebase...")
        self.rafraichir_poll()

    def rafraichir_poll(self):
        def lire():
            try:
                data = db.child("capteurs").child(self.uid).get()
                if data.val():
                    d = data.val()
                    self.after(0, lambda: self.mettre_a_jour(d))
                    self.after(0, lambda: self.sauvegarder_db(d))

                # je lis aussi l'etat actuel de la pompe et du ventilo
                cmds = db.child("commandes").child(self.uid).get()
                if cmds.val():
                    vals = cmds.val()
                    pompe_on = bool(vals.get("pompe", False))
                    ventilo_on = bool(vals.get("ventilateur", False))
                    self.after(0, lambda: self.mettre_a_jour_actionneurs(pompe_on, ventilo_on))

            except Exception as e:
                self.after(0, lambda: self.log("ERROR", "Firebase: " + str(e)))

            # je re-programme la lecture dans 3 secondes
            self.after(3000, self.rafraichir_poll)

        threading.Thread(target=lire, daemon=True).start()

    # je mets a jour l'affichage des actionneurs
    def mettre_a_jour_actionneurs(self, pompe_on, ventilo_on):
        if pompe_on:
            self.lbl_pompe.configure(text="[ON]", fg=VERT)
            if not self.mode_auto:
                self.btn_pompe.configure(text="[DESACTIVER]", bg=ROUGE, fg=TEXTE)
        else:
            self.lbl_pompe.configure(text="[OFF]", fg=ROUGE)
            if not self.mode_auto:
                self.btn_pompe.configure(text="[ACTIVER]", bg=ACCENT, fg=FOND)
        self.pompe_on = pompe_on

        if ventilo_on:
            self.lbl_ventilo.configure(text="[ON]", fg=VERT)
            if not self.mode_auto:
                self.btn_ventilo.configure(text="[DESACTIVER]", bg=ROUGE, fg=TEXTE)
        else:
            self.lbl_ventilo.configure(text="[OFF]", fg=ROUGE)
            if not self.mode_auto:
                self.btn_ventilo.configure(text="[ACTIVER]", bg=ACCENT, fg=FOND)
        self.ventilo_on = ventilo_on

    # je sauvegarde les donnees dans mysql
    def sauvegarder_db(self, d):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO capteurs (uid, temperature, humidite_air, humidite_sol, pluie) VALUES (%s,%s,%s,%s,%s)",
                (self.uid,
                 d.get("temperature"),
                 d.get("humidite_air"),
                 d.get("humidite_sol"),
                 d.get("pluie", False))
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            self.log("ERROR", "MariaDB: " + str(e))

    # je mets a jour les valeurs des capteurs dans l'interface
    def mettre_a_jour(self, d):
        temp = d.get("temperature", "--")
        hum = d.get("humidite_air", "--")
        sol = d.get("humidite_sol", "--")
        pluie = d.get("pluie", False)

        # couleur et valeur pour chaque capteur
        if isinstance(temp, (int, float)):
            couleur_temp = ROUGE if temp > 30 else VERT
            ratio_temp = min(temp / 50, 1)
            txt_temp = str(temp) + "C"
        else:
            couleur_temp = GRIS
            ratio_temp = 0.5
            txt_temp = "--"

        if isinstance(hum, (int, float)):
            couleur_hum = ORANGE if hum < 40 else VERT
            ratio_hum = hum / 100
            txt_hum = str(hum) + "%"
        else:
            couleur_hum = GRIS
            ratio_hum = 0.5
            txt_hum = "--"

        if isinstance(sol, (int, float)):
            couleur_sol = ROUGE if sol < 30 else VERT
            ratio_sol = sol / 100
            txt_sol = str(sol) + "%"
        else:
            couleur_sol = GRIS
            ratio_sol = 0.5
            txt_sol = "--"

        couleur_pluie = BLEU if pluie else GRIS
        txt_pluie = "OUI" if pluie else "NON"
        ratio_pluie = 1.0 if pluie else 0.05

        # je mets a jour chaque ligne
        lbl, bar = self._vals["temp"]
        lbl.configure(text=txt_temp, fg=couleur_temp)
        bar.configure(bg=couleur_temp)
        bar.place(relwidth=ratio_temp)

        lbl, bar = self._vals["hum"]
        lbl.configure(text=txt_hum, fg=couleur_hum)
        bar.configure(bg=couleur_hum)
        bar.place(relwidth=ratio_hum)

        lbl, bar = self._vals["sol"]
        lbl.configure(text=txt_sol, fg=couleur_sol)
        bar.configure(bg=couleur_sol)
        bar.place(relwidth=ratio_sol)

        lbl, bar = self._vals["pluie"]
        lbl.configure(text=txt_pluie, fg=couleur_pluie)
        bar.configure(bg=couleur_pluie)
        bar.place(relwidth=ratio_pluie)

        self.log("DATA", "T:" + str(temp) + "C H:" + str(hum) + "% Sol:" + str(sol) + "% Pluie:" + txt_pluie)
        self.lbl_statut.configure(
            text="[" + time.strftime("%H:%M:%S") + "] Derniere mise a jour",
            fg=GRIS)

        # alertes si une plante est active
        if self.plante_active:
            p = self.plante_active
            if isinstance(temp, (int, float)) and temp > p["temp_max"]:
                self.log("WARN", "[ALERTE] " + p["nom"] + " : Temperature trop haute ! (" + str(temp) + "C > " + str(p["temp_max"]) + "C)")
            if isinstance(hum, (int, float)) and hum < p["humidite_min"]:
                self.log("WARN", "[ALERTE] " + p["nom"] + " : Humidite trop basse ! (" + str(hum) + "% < " + str(p["humidite_min"]) + "%)")
            if isinstance(sol, (int, float)) and sol < p["eau_min"]:
                self.log("WARN", "[ALERTE] " + p["nom"] + " : Sol trop sec ! (" + str(sol) + "% < " + str(p["eau_min"]) + "%)")

    def deconnexion(self):
        if self.page_principale:
            self.page_principale = None
        self.quand_deconnecte()


# ---- application principale ----
class App:
    def __init__(self):
        self.fen = tk.Tk()
        self.fen.title("Serre Connectee")
        self.fen.configure(bg=FOND)
        self.fen.geometry("980x750")
        self.fen.resizable(False, False)
        init_db()
        self.page = None
        self.afficher_connexion()

    def afficher_connexion(self):
        if self.page:
            self.page.destroy()
        self.page = PageConnexion(self.fen, self.afficher_dashboard)
        self.page.pack(fill="both", expand=True)

    def afficher_dashboard(self, uid, email):
        if self.page:
            self.page.destroy()
        self.page = PageDashboard(self.fen, uid, email, self.afficher_connexion)
        self.page.pack(fill="both", expand=True)

    def run(self):
        self.fen.mainloop()


if __name__ == "__main__":
    App().run()
