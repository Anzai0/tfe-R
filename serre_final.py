# -*- coding: utf-8 -*-
import time
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from gpiozero import TonalBuzzer, OutputDevice
from gpiozero.tones import Tone
import pyrebase
import pymysql
import os
import json
import getpass

pymysql.install_as_MySQLdb()

os.environ['GPIOZERO_PIN_FACTORY'] = 'rpigpio'

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
    return {"nom": "Plante", "temp_max": 30.0, "eau_min": 40.0}

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
        print(f"[MariaDB] Capteurs envoyés ✓")
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

# ─── LCD ──────────────────────────────────────────────────────────────────────
def init_lcd():
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
        lcd.clear()
        return lcd
    except Exception as e:
        print(f"[LCD] Erreur init: {e}")
        return None

def lcd_write_safe(lcd, line1, line2=""):
    try:
        if lcd is None:
            lcd = init_lcd()
        if lcd:
            lcd.clear()
            lcd.write_string(line1[:16])
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2[:16])
    except Exception as e:
        print(f"[LCD] Erreur écriture: {e}")
        try:
            lcd = init_lcd()
        except:
            lcd = None
    return lcd

# ─── ADS1115 ──────────────────────────────────────────────────────────────────
def init_ads():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        capteur_pluie = AnalogIn(ads, ADS.P0)
        capteur_sol = AnalogIn(ads, ADS.P1)
        print("[ADS1115] Initialisé ✓")
        return capteur_pluie, capteur_sol
    except Exception as e:
        print(f"[ADS1115] Erreur init: {e}")
        return None, None

# ─── Lecture humidité sol ─────────────────────────────────────────────────────
def lire_humidite_sol(capteur_sol):
    try:
        val_brute = capteur_sol.value
        val_min = 6000
        val_max = 26000
        pourcentage = ((val_max - val_brute) / (val_max - val_min)) * 100
        pourcentage = max(0, min(100, pourcentage))
        return round(pourcentage, 1)
    except Exception as e:
        print(f"[Sol] Erreur lecture: {e}")
        return 0

# ─── Lecture pluie ────────────────────────────────────────────────────────────
def lire_pluie(capteur_pluie):
    try:
        return capteur_pluie.value < 10000
    except Exception as e:
        print(f"[Pluie] Erreur lecture: {e}")
        return False

# ─── Buzzer ──────────────────────────────────────────────────────────────────
def init_buzzer():
    try:
        buzzer = TonalBuzzer(18)
        return buzzer
    except Exception as e:
        print(f"[Buzzer] Erreur init: {e}")
        return None

def buzzer_alerte(buzzer):
    try:
        if buzzer:
            buzzer.play(Tone("A4"))
            time.sleep(0.3)
            buzzer.stop()
    except Exception as e:
        print(f"[Buzzer] Erreur: {e}")

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
    print("[Système] Démarrage...")
    
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
    
    # Initialisations hardware
    dht = adafruit_dht.DHT11(board.D4)
    capteur_pluie, capteur_sol = init_ads()
    buzzer = init_buzzer()
    lcd = init_lcd()
    
    # Relais
    pompe = OutputDevice(17)
    ventilateur = OutputDevice(27)
    pompe.off()
    ventilateur.off()
    
    # États
    etat_pompe = False
    etat_ventilo = False
    mode_auto = True
    firebase_counter = 0
    
    print("[Système] Démarrage boucle principale...")
    
    try:
        while True:
            # ── Lecture capteurs ──────────────────────────────────────────
            try:
                temp = dht.temperature
                hum = dht.humidity
            except:
                temp, hum = None, None
            
            pourcentage_sol = lire_humidite_sol(capteur_sol) if capteur_sol else 0
            pluie = lire_pluie(capteur_pluie) if capteur_pluie else False
            
            # ── Lecture commandes Firebase ────────────────────────────────
            commandes = lire_commandes_firebase(uid)
            mode_auto = commandes.get("mode_auto", True)
            
            if mode_auto:
                # Logique automatique
                etat_pompe, etat_ventilo = logique_automatique(
                    temp or 25, pourcentage_sol, config_plante, mode_auto
                )
            else:
                # Manuel depuis Firebase
                etat_pompe = commandes.get("pompe", False)
                etat_ventilo = commandes.get("ventilateur", False)
            
            # ── Contrôle relais ──────────────────────────────────────────
            if etat_pompe:
                pompe.on()
            else:
                pompe.off()
            
            if etat_ventilo:
                ventilateur.on()
            else:
                ventilateur.off()
            
            # ── Affichage LCD ────────────────────────────────────────────
            if temp is not None and hum is not None:
                lcd = lcd_write_safe(
                    lcd,
                    f"T:{temp:.1f}°C H:{hum:.0f}%",
                    f"Sol:{pourcentage_sol:.0f}% P:{etat_pompe} V:{etat_ventilo}"
                )
            
            # ── Envoi MariaDB ────────────────────────────────────────────
            firebase_counter += 1
            if firebase_counter >= 2:
                firebase_counter = 0
                if temp is not None and hum is not None:
                    envoyer_capteurs_mariadb(
                        uid,
                        round(temp, 1),
                        round(hum, 1),
                        round(pourcentage_sol, 1),
                        pluie,
                        etat_pompe,
                        etat_ventilo
                    )
            
            # ── Console ──────────────────────────────────────────────────
            status = f"T:{temp or '--'}°C | H:{hum or '--'}% | " \
                    f"Sol:{pourcentage_sol:.0f}% | Pluie:{pluie} | " \
                    f"Pompe:{etat_pompe} | Ventilo:{etat_ventilo} | " \
                    f"Mode:{'AUTO' if mode_auto else 'MANUEL'}"
            print(status)
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n[Système] Arrêt...")
        pompe.off()
        ventilateur.off()
        if lcd:
            lcd_write_safe(lcd, "Systeme arrete", "")
        print("[Système] ✓ Arrêt propre.")
