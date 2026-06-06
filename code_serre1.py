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

def connect_firebase():
    config = charger_config()
    if config:
        print(f"=== Utilisateur connecté : {config['email']} ===")
        choix = input("Changer d'utilisateur ? (o/n) : ").strip().lower()
        if choix == 'o':
            os.remove(CONFIG_FILE)
            config = None

    if not config:
        print("=== Connexion ===")
        email    = input("Email    : ")
        password = input("Password : ")
        sauvegarder_config(email, password)
    else:
        email    = config["email"]
        password = config["password"]

    try:
        user = auth_fb.sign_in_with_email_and_password(email, password)
        uid  = user["localId"]
        print(f"[Firebase] Connecte : {email}")
        return uid
    except Exception as e:
        print(f"[Firebase] Erreur: {e}")
        os.remove(CONFIG_FILE)
        return connect_firebase()

def reset_commandes_firebase(uid):
    try:
        db.child("commandes").child(uid).set({
            "pompe":       False,
            "ventilateur": False,
            "auto":        False   # ← mode auto désactivé par défaut
        })
        print("[Firebase] Commandes remises a zero")
    except Exception as e:
        print(f"[Firebase] Erreur reset commandes: {e}")

def envoyer_firebase(uid, temp, hum, sol, pluie, etat_pompe, etat_ventilo, mode_auto, plante_active):
    try:
        data = {
            "temperature":   temp  if temp is not None else 0,
            "humidite_air":  hum   if hum  is not None else 0,
            "humidite_sol":  sol   if sol  is not None else 0,
            "pluie":         bool(pluie),
            "pompe":         etat_pompe   == "ON",
            "ventilateur":   etat_ventilo == "ON",
            "mode_auto":     mode_auto,
            "plante_active": plante_active if plante_active else "aucune",
            "timestamp":     time.strftime("%Y-%m-%d %H:%M:%S")
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
    """
    Retourne les seuils de la plante sélectionnée ou None.
    Structure Firebase attendue :
    plantes/{uid}/{nom_plante} : {
        "seuil_humidite_air": 60,
        "seuil_humidite_sol": 35,
        "seuil_temperature":  25,
        "selectionnee": true    ← une seule plante a ce champ à true
    }
    """
    try:
        plantes = db.child("plantes").child(uid).get().val()
        if not plantes:
            return None, None

        for nom, data in plantes.items():
            if isinstance(data, dict) and data.get("selectionnee", False):
                return nom, data

        return None, None
    except Exception as e:
        print(f"[Firebase] Erreur lecture plantes: {e}")
        return None, None

# ─── Matériel ─────────────────────────────────────────────
lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
dht = adafruit_dht.DHT11(board.D17, use_pulseio=False)
time.sleep(2)

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
sol_last         = None
pluie_last       = False
firebase_counter = 0

cmd_pompe_manuelle   = None
cmd_ventilo_manuelle = None
mode_auto            = False   # ← mode auto

# Seuils par défaut (utilisés si aucune plante sélectionnée)
SEUIL_SOL_DEFAULT  = 30
SEUIL_TEMP_DEFAULT = 30
SEUIL_HUM_DEFAULT  = 70

# ─── Connexion Firebase ───────────────────────────────────
uid = connect_firebase()
if uid:
    reset_commandes_firebase(uid)
else:
    print("[WARN] Mode local uniquement (pas de Firebase)")

# ─── Boucle principale ────────────────────────────────────
try:
    while True:

        # ── Lecture DHT11 ────────────────────────────────
        try:
            temp = dht.temperature
            hum  = dht.humidity
            temp_last = temp
            hum_last  = hum
        except Exception:
            temp = temp_last
            hum  = hum_last

        # ── Lecture ADS1115 ──────────────────────────────
        try:
            valeur_pluie    = capteur_pluie.value
            valeur_sol      = capteur_sol.value
            pourcentage_sol = round((1 - valeur_sol / 32767) * 100, 1)
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

        # ── Lecture commandes + mode auto depuis Firebase ─
        if uid:
            cmds = lire_commandes_firebase(uid)
            mode_auto = bool(cmds.get("auto", False))

            if not mode_auto:
                # Mode manuel : on lit les commandes manuelles
                if "pompe" in cmds:
                    cmd_pompe_manuelle = bool(cmds["pompe"])
                if "ventilateur" in cmds:
                    cmd_ventilo_manuelle = bool(cmds["ventilateur"])
            else:
                # Mode auto : on ignore les commandes manuelles
                cmd_pompe_manuelle   = None
                cmd_ventilo_manuelle = None

        # ── Lecture plante sélectionnée ──────────────────
        plante_nom, plante_data = None, None
        if uid and mode_auto:
            plante_nom, plante_data = lire_plante_active(uid)

        # ── Récupération des seuils ──────────────────────
        if plante_data:
            seuil_sol  = plante_data.get("seuil_humidite_sol", SEUIL_SOL_DEFAULT)
            seuil_temp = plante_data.get("seuil_temperature",  SEUIL_TEMP_DEFAULT)
            seuil_hum  = plante_data.get("seuil_humidite_air", SEUIL_HUM_DEFAULT)
        else:
            seuil_sol  = SEUIL_SOL_DEFAULT
            seuil_temp = SEUIL_TEMP_DEFAULT
            seuil_hum  = SEUIL_HUM_DEFAULT

        # ── Gestion Pompe ────────────────────────────────
        if mode_auto:
            # Auto : pompe si sol sec et pas de pluie
            if pourcentage_sol is not None and pourcentage_sol < seuil_sol and not pluie:
                pompe.value = True
                etat_pompe  = "ON"
            else:
                pompe.value = False
                etat_pompe  = "OFF"
        else:
            # Manuel
            if cmd_pompe_manuelle is not None:
                pompe.value = cmd_pompe_manuelle
                etat_pompe  = "ON" if cmd_pompe_manuelle else "OFF"
            else:
                pompe.value = False
                etat_pompe  = "OFF"

        # ── Gestion Ventilateur ──────────────────────────
        if mode_auto:
            # Auto : ventilo si humidité trop haute OU température trop haute
            ventilo_on = False
            if hum  is not None and hum  > seuil_hum:
                ventilo_on = True
            if temp is not None and temp > seuil_temp:
                ventilo_on = True
            ventilateur.value = ventilo_on
            etat_ventilo      = "ON" if ventilo_on else "OFF"
        else:
            # Manuel
            if cmd_ventilo_manuelle is not None:
                ventilateur.value = cmd_ventilo_manuelle
                etat_ventilo      = "ON" if cmd_ventilo_manuelle else "OFF"
            else:
                ventilateur.value = False
                etat_ventilo      = "OFF"

        # ── Buzzer ───────────────────────────────────────
        if temp is not None and temp > 35:
            buzzer.play(Tone(2000))
            time.sleep(0.5)
            buzzer.stop()
        else:
            buzzer.stop()

        # ── Envoi Firebase toutes les ~6s ────────────────
        firebase_counter += 1
        if uid and firebase_counter >= 3:
            envoyer_firebase(uid, temp, hum, pourcentage_sol,
                             pluie, etat_pompe, etat_ventilo,
                             mode_auto, plante_nom)
            firebase_counter = 0

        # ── Print console ────────────────────────────────
        print("=" * 35)
        print(f"Mode    : {'AUTO' if mode_auto else 'MANUEL'}")
        print(f"Plante  : {plante_nom if plante_nom else 'aucune'}")
        print(f"Seuils  : Sol<{seuil_sol}% | Hum>{seuil_hum}% | Temp>{seuil_temp}C")
        print(f"Temp    : {temp}C"            if temp            else "Temp    : --")
        print(f"Humidite: {hum}%"             if hum             else "Humidite: --")
        print(f"Sol     : {pourcentage_sol}%" if pourcentage_sol else "Sol     : --")
        print(f"Pluie   : {'OUI' if pluie else 'NON'}")
        print(f"Pompe   : {etat_pompe}")
        print(f"Ventilo : {etat_ventilo}")
        print("=" * 35)

        # ── LCD ──────────────────────────────────────────
        lcd.clear()
        if ecran == 0:
            lcd.write_string(f"T:{temp:.1f}C"          if temp else "T:--")
            lcd.cursor_pos = (1, 0)
            lcd.write_string(f"Hum:{hum:.1f}%"         if hum  else "H:--")
        elif ecran == 1:
            lcd.write_string(f"Sol:{pourcentage_sol}%" if pourcentage_sol else "Sol:--")
            lcd.cursor_pos = (1, 0)
            lcd.write_string("PLUIE!" if pluie else "Pas de pluie")
        elif ecran == 2:
            lcd.write_string(f"P:{etat_pompe} V:{etat_ventilo}")
            lcd.cursor_pos = (1, 0)
            # Affiche la plante active ou le mode
            lcd.write_string(
                f"{'AUTO' if mode_auto else 'MAN'} {plante_nom[:8] if plante_nom else 'aucune'}"
            )

        ecran = (ecran + 1) % 3
        time.sleep(2)

finally:
    pompe.value = False
    pompe.deinit()
    ventilateur.value = False
    ventilateur.deinit()
    buzzer.stop()
    dht.exit()
    lcd.clear()
    if uid:
        reset_commandes_firebase(uid)
    print("Systeme arrete")
