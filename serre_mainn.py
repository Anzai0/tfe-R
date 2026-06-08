# -*- coding: utf-8 -*-
import time
import board
import busio
import digitalio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from RPLCD.i2c import CharLCD
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
import pyrebase
import os
import json

os.environ['GPIOZERO_PIN_FACTORY'] = 'rpigpio'

# ─── Firebase ────────────────────────────────────────────
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
auth_fb  = firebase.auth()
db       = firebase.database()

CONFIG_FILE = "config.json"

def charger_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def sauvegarder_config(email, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"email": email, "password": password}, f)

# BUG CORRIGE : config = None empechait de charger le fichier
def connect_firebase():
    config = charger_config()  # ← était "config = None" !!
    if config:
        print(f"=== Utilisateur connecte : {config['email']} ===")
    else:
        print("=== Premiere connexion ===")
        email    = input("Email    : ")
        password = input("Password : ")
        sauvegarder_config(email, password)
        config = {"email": email, "password": password}
    try:
        user = auth_fb.sign_in_with_email_and_password(
            config["email"], config["password"])
        uid  = user["localId"]
        print(f"[Firebase] Connecte : {config['email']}")
        return uid
    except Exception as e:
        err = str(e)
        print(f"[Firebase] Erreur: {err}")
        # Ne supprime le fichier QUE si mauvais mot de passe
        # pas si c'est un probleme reseau
        if "INVALID_PASSWORD" in err or "EMAIL_NOT_FOUND" in err or "INVALID_LOGIN" in err:
            os.remove(CONFIG_FILE)
            return connect_firebase()
        else:
            print("[Firebase] Probleme reseau, nouvelle tentative dans 5s...")
            time.sleep(5)
            return connect_firebase()

def reset_commandes_firebase(uid):
    try:
        db.child("commandes").child(uid).set({
            "pompe":       False,
            "ventilateur": False,
            "auto":        False
        })
        print("[Firebase] Commandes remises a zero")
    except Exception as e:
        print(f"[Firebase] Erreur reset: {e}")

def envoyer_firebase(uid, temp, hum, sol, pluie, etat_pompe, etat_ventilo):
    try:
        data = {
            "temperature":  temp  if temp is not None else 0,
            "humidite_air": hum   if hum  is not None else 0,
            "humidite_sol": sol   if sol  is not None else 0,
            "pluie":        bool(pluie),
            "pompe":        etat_pompe   == "ON",
            "ventilateur":  etat_ventilo == "ON",
            "timestamp":    time.strftime("%Y-%m-%d %H:%M:%S")
        }
        db.child("capteurs").child(uid).set(data)
        print("[Firebase] Donnees envoyees OK")
    except Exception as e:
        print(f"[Firebase] Erreur envoi: {e}")

def lire_commandes_firebase(uid):
    try:
        cmds = db.child("commandes").child(uid).get().val()
        return cmds if cmds else {}
    except Exception as e:
        print(f"[Firebase] Erreur lecture commandes: {e}")
        return {}

def lire_plante_active(uid):
    try:
        cmds      = db.child("commandes").child(uid).get().val() or {}
        mode_auto = bool(cmds.get("auto", False))
        plante    = db.child("plantes_actives").child(uid).get().val()
        return mode_auto, plante
    except Exception as e:
        print(f"[Firebase] Erreur lecture plante: {e}")
        return False, None

# ─── Matériel ─────────────────────────────────────────────
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)

# BUG CORRIGE : DHT11 sur D4, pas D17 (D17 = pompe)
dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)
time.sleep(2)

# BUG CORRIGE : pompe sur D18, ventilo sur D23
pompe = digitalio.DigitalInOut(board.D18)
pompe.direction = digitalio.Direction.OUTPUT

ventilateur = digitalio.DigitalInOut(board.D23)
ventilateur.direction = digitalio.Direction.OUTPUT

buzzer = TonalBuzzer(27)

def init_ads():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    return AnalogIn(ads, 0), AnalogIn(ads, 1)

capteur_pluie, capteur_sol = init_ads()

# ─── Variables ────────────────────────────────────────────
ecran            = 0
temp_last        = None
hum_last         = None
sol_last         = 0       # BUG CORRIGE : etait None, causait erreur calcul
pluie_last       = False
firebase_counter = 0

cmd_pompe_manuelle   = None
cmd_ventilo_manuelle = None
mode_auto            = False
plante_active        = None
etat_pompe           = "OFF"   # BUG CORRIGE : variables initialisees
etat_ventilo         = "OFF"   # pour eviter NameError au premier tour

# ─── Connexion Firebase ───────────────────────────────────
uid = connect_firebase()
if uid:
    reset_commandes_firebase(uid)
else:
    print("[WARN] Mode local uniquement")

# ─── Boucle principale ────────────────────────────────────
try:
    while True:

        # ── Lecture DHT11 ────────────────────────────────
        try:
            t = dht.temperature
            h = dht.humidity
            if t is not None:
                temp_last = t
            if h is not None:
                hum_last = h
            temp = temp_last
            hum  = hum_last
        except Exception:
            temp = temp_last
            hum  = hum_last

        # ── Lecture ADS1115 ──────────────────────────────
        try:
            valeur_pluie    = capteur_pluie.value
            valeur_sol      = capteur_sol.value
            pourcentage_sol = round((1 - valeur_sol / 32767) * 100, 1)
            # BUG CORRIGE : clamp entre 0 et 100
            pourcentage_sol = max(0.0, min(100.0, pourcentage_sol))
            pluie           = valeur_pluie < 26500
            sol_last        = pourcentage_sol
            pluie_last      = pluie
        except Exception:
            try:
                capteur_pluie, capteur_sol = init_ads()
            except:
                pass
            pourcentage_sol = sol_last
            pluie           = pluie_last

        # ── Lecture commandes + plante depuis Firebase ───
        if uid:
            cmds = lire_commandes_firebase(uid)
            mode_auto, plante_active = lire_plante_active(uid)

            if not mode_auto:
                if "pompe" in cmds:
                    cmd_pompe_manuelle = bool(cmds["pompe"])
                if "ventilateur" in cmds:
                    cmd_ventilo_manuelle = bool(cmds["ventilateur"])
            else:
                cmd_pompe_manuelle   = None
                cmd_ventilo_manuelle = None

        # ── Seuils plante active ─────────────────────────
        if plante_active and isinstance(plante_active, dict):
            seuil_sol  = plante_active.get("eau_min",      30)
            seuil_hum  = plante_active.get("humidite_min", 60)
            seuil_temp = plante_active.get("temp_max",     30)
        else:
            seuil_sol  = 30
            seuil_hum  = 60
            seuil_temp = 30

        # ── Gestion Pompe ────────────────────────────────
        if cmd_pompe_manuelle is not None:
            pompe.value = cmd_pompe_manuelle
            etat_pompe  = "ON" if cmd_pompe_manuelle else "OFF"
        else:
            if pourcentage_sol < seuil_sol and not pluie:
                pompe.value = True
                etat_pompe  = "ON"
            else:
                pompe.value = False
                etat_pompe  = "OFF"

        # ── Gestion Ventilateur ──────────────────────────
        if cmd_ventilo_manuelle is not None:
            ventilateur.value = cmd_ventilo_manuelle
            etat_ventilo      = "ON" if cmd_ventilo_manuelle else "OFF"
        else:
            if ((hum  is not None and hum  > seuil_hum) or
                    (temp is not None and temp > seuil_temp)):
                ventilateur.value = True
                etat_ventilo      = "ON"
            else:
                ventilateur.value = False
                etat_ventilo      = "OFF"

        # ── Buzzer ───────────────────────────────────────
        if temp is not None and temp > 35:
            try:
                buzzer.play(Tone(2000))
                time.sleep(0.5)
                buzzer.stop()
            except:
                pass
        else:
            try:
                buzzer.stop()
            except:
                pass

        # ── Envoi Firebase toutes les ~6s ────────────────
        firebase_counter += 1
        if uid and firebase_counter >= 3:
            envoyer_firebase(uid, temp, hum, pourcentage_sol,
                              pluie, etat_pompe, etat_ventilo)
            firebase_counter = 0

        # ── Print console ────────────────────────────────
        # BUG CORRIGE : plante_active peut etre un dict ou None
        if plante_active and isinstance(plante_active, dict):
            nom_plante = plante_active.get("nom", "aucune")
        else:
            nom_plante = "aucune"

        print("=" * 30)
        print(f"Mode    : {'AUTO' if mode_auto else 'MANUEL'} ({nom_plante})")
        print(f"Temp    : {temp}C"            if temp is not None else "Temp    : --")
        print(f"Humidite: {hum}%"             if hum  is not None else "Humidite: --")
        print(f"Sol     : {pourcentage_sol}%")
        print(f"Pluie   : {'OUI' if pluie else 'NON'}")
        print(f"Pompe   : {etat_pompe}")
        print(f"Ventilo : {etat_ventilo}")
        print("=" * 30)

        # ── LCD ──────────────────────────────────────────
        try:
            lcd.clear()
            if ecran == 0:
                lcd.write_string(f"T:{temp:.1f}C" if temp is not None else "T:--")
                lcd.cursor_pos = (1, 0)
                lcd.write_string(f"Hum:{hum:.1f}%" if hum is not None else "H:--")
            elif ecran == 1:
                lcd.write_string(f"Sol:{pourcentage_sol}%")
                lcd.cursor_pos = (1, 0)
                lcd.write_string("PLUIE!" if pluie else "Pas de pluie")
            elif ecran == 2:
                lcd.write_string(f"P:{etat_pompe} V:{etat_ventilo}")
                lcd.cursor_pos = (1, 0)
                mode_txt   = "AUTO" if mode_auto else "MAN"
                plante_txt = nom_plante[:8] if nom_plante != "aucune" else "aucune"
                lcd.write_string(f"{mode_txt} {plante_txt}")
        except Exception as e:
            print(f"[LCD] Erreur: {e}")

        ecran = (ecran + 1) % 3
        time.sleep(2)

finally:
    pompe.value = False
    pompe.deinit()
    ventilateur.value = False
    ventilateur.deinit()
    try:
        buzzer.stop()
    except:
        pass
    dht.exit()
    lcd.clear()
    if uid:
        reset_commandes_firebase(uid)
    print("Systeme arrete")
