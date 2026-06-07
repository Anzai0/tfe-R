# -*- coding: utf-8 -*-
# code principal de la serre connectee
# gere les capteurs, le lcd, le buzzer et firebase

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

# infos pour se connecter a firebase
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

# je charge la config sauvegardee si elle existe
def charger_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

# je sauvegarde l'email et le mot de passe pour pas les retaper
def sauvegarder_config(email, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"email": email, "password": password}, f)

# connexion a firebase
def connect_firebase():
    config = charger_config()
    if config:
        print("=== Utilisateur connecte : " + config['email'] + " ===")
    else:
        print("=== Premiere connexion ===")
        email = input("Email    : ")
        password = input("Password : ")
        sauvegarder_config(email, password)
        config = {"email": email, "password": password}
    try:
        user = auth_fb.sign_in_with_email_and_password(config["email"], config["password"])
        uid = user["localId"]
        print("[Firebase] Connecte : " + config['email'])
        return uid
    except Exception as e:
        print("[Firebase] Erreur: " + str(e))
        os.remove(CONFIG_FILE)
        return connect_firebase()

# je remet les commandes a zero quand on arrete le programme
def reset_commandes_firebase(uid):
    try:
        db.child("commandes").child(uid).set({
            "pompe": False,
            "ventilateur": False,
            "auto": False
        })
        print("[Firebase] Commandes remises a zero")
    except Exception as e:
        print("[Firebase] Erreur reset: " + str(e))

# envoie les donnees des capteurs sur firebase
def envoyer_donnees_firebase(uid, temp, hum, sol, pluie):
    try:
        db.child("capteurs").child(uid).set({
            "temperature": temp,
            "humidite_air": hum,
            "humidite_sol": sol,
            "pluie": pluie
        })
    except Exception as e:
        print("[Firebase] Erreur envoi: " + str(e))

# je lis les commandes envoyees depuis l'application
def lire_commandes_firebase(uid):
    try:
        data = db.child("commandes").child(uid).get()
        if data.val():
            return data.val()
    except Exception as e:
        print("[Firebase] Erreur lecture commandes: " + str(e))
    return {}

# je lis quelle plante est active et si le mode auto est active
def lire_plante_active(uid):
    try:
        data = db.child("commandes").child(uid).get()
        if data.val():
            vals = data.val()
            mode_auto = bool(vals.get("auto", False))
            plante = vals.get("plante_active", None)
            return mode_auto, plante
    except Exception as e:
        print("[Firebase] Erreur lecture plante: " + str(e))
    return False, None

# initialisation du capteur dht22 (temperature et humidite)
def init_dht():
    dht = adafruit_dht.DHT22(board.D4)
    return dht

# initialisation de l'ads1115 pour lire le capteur sol et pluie
def init_ads():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    capteur_pluie = AnalogIn(ads, ADS.P0)
    capteur_sol = AnalogIn(ads, ADS.P1)
    return capteur_pluie, capteur_sol

# je configure la pompe et le ventilateur
import gpiozero
pompe = gpiozero.OutputDevice(17, active_high=True, initial_value=False)
ventilateur = gpiozero.OutputDevice(27, active_high=True, initial_value=False)

# le buzzer pour les alertes
buzzer = TonalBuzzer(18)

# l'ecran lcd
lcd = CharLCD('PCF8574', 0x27)

# je lance la connexion firebase
uid = connect_firebase()
reset_commandes_firebase(uid)

# je configure le capteur dht
dht = init_dht()
capteur_pluie, capteur_sol = init_ads()

# variables pour garder les dernieres valeurs si un capteur plante
temp = None
hum = None
sol_last = 0
pluie_last = False
pourcentage_sol = 0
pluie = False

# variables pour les commandes manuelles
cmd_pompe_manuelle = False
cmd_ventilo_manuelle = False
mode_auto = False
plante_active = None
nom_plante = ""

ecran = 0  # pour changer ce qui s'affiche sur le lcd

print("[Systeme] Demarrage...")

try:
    while True:

        # lecture du capteur temperature / humidite
        try:
            temp = dht.temperature
            hum = dht.humidity
        except Exception:
            pass  # je garde les anciennes valeurs si ca marche pas

        # lecture des capteurs analogiques (sol et pluie)
        try:
            valeur_pluie = capteur_pluie.value
            valeur_sol = capteur_sol.value
            pourcentage_sol = round((1 - valeur_sol / 32767) * 100, 1)
            pluie = valeur_pluie < 26500
            sol_last = pourcentage_sol
            pluie_last = pluie
        except Exception:
            try:
                capteur_pluie, capteur_sol = init_ads()
            except:
                pass
            pourcentage_sol = sol_last
            pluie = pluie_last

        # je lis les commandes et la plante depuis firebase
        if uid:
            cmds = lire_commandes_firebase(uid)
            mode_auto, plante_active = lire_plante_active(uid)

            if not mode_auto:
                # mode manuel : je lis ce que l'utilisateur a choisi dans l'app
                if "pompe" in cmds:
                    cmd_pompe_manuelle = bool(cmds["pompe"])
                if "ventilateur" in cmds:
                    cmd_ventilo_manuelle = bool(cmds["ventilateur"])
            else:
                # mode auto : les boutons manuels sont ignores
                cmd_pompe_manuelle = None
                cmd_ventilo_manuelle = None

        # je recupere le nom de la plante active
        if plante_active and isinstance(plante_active, dict):
            nom_plante = plante_active.get("nom", "")
        else:
            nom_plante = ""

        # logique automatique selon les seuils de la plante
        if mode_auto and plante_active and isinstance(plante_active, dict):
            temp_max = plante_active.get("temp_max", 30)
            eau_min = plante_active.get("eau_min", 30)

            # si trop chaud j'active le ventilateur
            if temp and temp > temp_max:
                ventilateur.on()
                etat_ventilo = "ON"
            else:
                ventilateur.off()
                etat_ventilo = "OFF"

            # si le sol est trop sec j'active la pompe
            if pourcentage_sol < eau_min:
                pompe.on()
                etat_pompe = "ON"
            else:
                pompe.off()
                etat_pompe = "OFF"

        else:
            # mode manuel
            if cmd_pompe_manuelle:
                pompe.on()
                etat_pompe = "ON"
            else:
                pompe.off()
                etat_pompe = "OFF"

            if cmd_ventilo_manuelle:
                ventilateur.on()
                etat_ventilo = "ON"
            else:
                ventilateur.off()
                etat_ventilo = "OFF"

        # j'envoie les donnees sur firebase
        if uid and temp and hum:
            envoyer_donnees_firebase(uid, temp, hum, pourcentage_sol, pluie)

        # buzzer si temperature trop haute
        if temp and temp > 35:
            try:
                buzzer.play(Tone("A4"))
                time.sleep(0.3)
                buzzer.stop()
            except:
                pass

        # affichage sur le lcd (je change d'ecran toutes les 2 secondes)
        try:
            lcd.clear()
            if ecran == 0:
                if temp:
                    lcd.write_string("T:" + str(round(temp, 1)) + "C")
                else:
                    lcd.write_string("T:--")
                lcd.cursor_pos = (1, 0)
                if hum:
                    lcd.write_string("Hum:" + str(round(hum, 1)) + "%")
                else:
                    lcd.write_string("H:--")

            elif ecran == 1:
                lcd.write_string("Sol:" + str(pourcentage_sol) + "%")
                lcd.cursor_pos = (1, 0)
                if pluie:
                    lcd.write_string("PLUIE!")
                else:
                    lcd.write_string("Pas de pluie")

            elif ecran == 2:
                lcd.write_string("P:" + etat_pompe + " V:" + etat_ventilo)
                lcd.cursor_pos = (1, 0)
                mode_txt = "AUTO" if mode_auto else "MAN"
                plante_txt = nom_plante[:8] if nom_plante else "aucune"
                lcd.write_string(mode_txt + " " + plante_txt)

        except Exception as e:
            print("[LCD] Erreur: " + str(e))

        ecran = (ecran + 1) % 3
        time.sleep(2)

# si on arrete le programme je remet tout a zero
finally:
    pompe.off()
    pompe.close()
    ventilateur.off()
    ventilateur.close()
    buzzer.stop()
    dht.exit()
    lcd.clear()
    if uid:
        reset_commandes_firebase(uid)
    print("Systeme arrete")
