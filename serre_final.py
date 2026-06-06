# -*- coding: utf-8 -*-
import time
import random
import pyrebase
import pymysql
import os
import json
import getpass
import threading

pymysql.install_as_MySQLdb()

# ─── Firebase (juste pour authentification) ────────────────────────────────────
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
auth_fb = firebase.auth()
db = firebase.database()

CONFIG_FILE = "config.json"

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
    """Crée les tables MariaDB si elles n'existent pas"""
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
        print("[DB] Tables créées/vérifiées ✓")
    except Exception as e:
        print(f"[DB] Erreur init: {e}")

# ─── Config locale ────────────────────────────────────────────────────────────
def charger_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def sauvegarder_config(email, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"email": email, "password": password}, f)
    print(f"[Config] Sauvegardée pour {email}")

# ─── Authentification Firebase ────────────────────────────────────────────────
def connexion_firebase(email, password):
    try:
        user = auth_fb.sign_in_with_email_and_password(email, password)
        uid = user["localId"]
        print(f"[Firebase] Connecté — UID: {uid}")
        return uid
    except Exception as e:
        print(f"[Firebase] Erreur connexion: {e}")
        return None

def demander_connexion():
    """Demande email/password à l'utilisateur et se connecte"""
    print("=" * 60)
    print("🌿 SERRE CONNECTÉE - Connexion")
    print("=" * 60)
    
    config = charger_config()
    
    if config:
        print(f"\n✓ Config trouvée pour: {config['email']}")
        utiliser = input("Utiliser cette config? (o/n): ").lower() == 'o'
        if utiliser:
            email = config["email"]
            password = config["password"]
        else:
            email = input("📧 Email: ")
            password = getpass.getpass("🔐 Mot de passe: ")
            sauvegarder_config(email, password)
    else:
        email = input("📧 Email: ")
        password = getpass.getpass("🔐 Mot de passe: ")
        sauvegarder_config(email, password)
    
    uid = connexion_firebase(email, password)
    return uid

# ─── Lecture config plante depuis Firebase ────────────────────────────────────
def lire_config_plante(uid):
    try:
        data = db.child("config_plante").child(uid).get().val()
        if data:
            return data
    except Exception as e:
        print(f"[Firebase] Erreur lecture config plante: {e}")
    return {"nom": "Ma plante", "temp_max": 30.0, "eau_min": 40.0}

# ─── Envoi capteurs à MariaDB ─────────────────────────────────────────────────
def envoyer_capteurs_mariadb(uid, temp, hum, sol, pluie, pompe, ventilo):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO capteurs "
            "(uid, temperature, humidite_air, humidite_sol, pluie, pompe, ventilateur) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (uid, temp, hum, sol, pluie, pompe, ventilo)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"[MariaDB] ✓ T:{temp:.1f}°C | H:{hum:.1f}% | Sol:{sol:.1f}% | P:{pompe} | V:{ventilo}")
    except Exception as e:
        print(f"[MariaDB] Erreur envoi: {e}")

# ─── Lecture des commandes depuis Firebase ────────────────────────────────────
def lire_commandes_firebase(uid):
    try:
        data = db.child("commandes").child(uid).get().val()
        if data:
            return data
    except Exception as e:
        print(f"[Firebase] Erreur lecture commandes: {e}")
    return {"pompe": False, "ventilateur": False, "mode_auto": True}

# ─── Reset commandes Firebase ─────────────────────────────────────────────────
def reset_commandes_firebase(uid):
    try:
        db.child("commandes").child(uid).set({
            "pompe": False,
            "ventilateur": False,
            "mode_auto": True
        })
        print("[Firebase] Commandes réinitialisées ✓")
    except Exception as e:
        print(f"[Firebase] Erreur reset: {e}")

# ─── Simulation capteurs ──────────────────────────────────────────────────────
class SimulateurCapteurs:
    def __init__(self):
        self.temp = 22.0
        self.hum = 50.0
        self.sol = 65.0
        self.pluie = False
        self.lock = threading.Lock()
    
    def lire(self):
        with self.lock:
            # Variation aléatoire réaliste
            self.temp += random.uniform(-0.5, 0.5)
            self.hum += random.uniform(-2, 2)
            self.sol += random.uniform(-1, 1)
            
            # Limites
            self.temp = max(15, min(35, self.temp))
            self.hum = max(30, min(95, self.hum))
            self.sol = max(20, min(100, self.sol))
            
            # Pluie aléatoire (10% de chance)
            self.pluie = random.random() < 0.1
            
            return self.temp, self.hum, self.sol, self.pluie

# ─── Logique auto (temp/humidité) ─────────────────────────────────────────────
def logique_automatique(temp, sol, config_plante, mode_auto):
    pompe_on = False
    ventilo_on = False
    
    if not mode_auto:
        return pompe_on, ventilo_on
    
    # Pompe si sol trop sec
    if sol < config_plante["eau_min"]:
        pompe_on = True
    
    # Ventilo si temp trop haute
    if temp > config_plante["temp_max"]:
        ventilo_on = True
    
    return pompe_on, ventilo_on

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[Système] Initialisation du matériel...")
    
    # Initialisation
    init_db()
    uid = demander_connexion()
    
    if not uid:
        print("[Système] Authentification échouée. Arrêt.")
        exit(1)
    
    # Charger config plante
    config_plante = lire_config_plante(uid)
    print(f"[Config] Plante: {config_plante['nom']} — "
          f"TempMax={config_plante['temp_max']}°C | "
          f"SolMin={config_plante['eau_min']}%")
    
    # Reset commandes
    reset_commandes_firebase(uid)
    
    # Simulateur (pas de capteurs physiques)
    sim = SimulateurCapteurs()
    
    # États
    etat_pompe = False
    etat_ventilo = False
    mode_auto = True
    
    print("[Système] Démarrage boucle principale...")
    print("[Système] Les données sont SIMULÉES (pas de capteurs physiques)")
    
    try:
        while True:
            # ── Lecture capteurs (simulés) ────────────────────────────────
            temp, hum, sol, pluie = sim.lire()
            
            # ── Lecture commandes Firebase ────────────────────────────────
            commandes = lire_commandes_firebase(uid)
            mode_auto = commandes.get("mode_auto", True)
            
            if mode_auto:
                # Logique automatique
                etat_pompe, etat_ventilo = logique_automatique(
                    temp, sol, config_plante, mode_auto
                )
            else:
                # Manuel depuis Firebase
                etat_pompe = commandes.get("pompe", False)
                etat_ventilo = commandes.get("ventilateur", False)
            
            # ── Envoi MariaDB ────────────────────────────────────────────
            envoyer_capteurs_mariadb(
                uid,
                round(temp, 1),
                round(hum, 1),
                round(sol, 1),
                pluie,
                etat_pompe,
                etat_ventilo
            )
            
            # ── Console ──────────────────────────────────────────────────
            status = f"Mode:{'AUTO' if mode_auto else 'MANUEL'} | " \
                    f"Pompe:{etat_pompe} | Ventilo:{etat_ventilo}"
            print(status)
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n[Système] Arrêt...")
        print("[Système] ✓ Arrêt propre.")
