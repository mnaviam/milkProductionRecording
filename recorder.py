import time
import RPi.GPIO as GPIO
from hx711 import HX711
import lcddriver
import requests
import json
import os
import threading
import socket
import config

# Pines HX711
DT_PIN = 5
SCK_PIN = 6

# Pines teclado (BCM)
L1, L2, L3, L4 = 12, 16, 20, 21
C1, C2, C3, C4 = 25, 8, 7, 1

keys = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in [L1, L2, L3, L4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
for pin in [C1, C2, C3, C4]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

lcd = lcddriver.lcd()
hx = HX711(DT_PIN, SCK_PIN)
hx.set_scale(105.5)

API_VERIFICAR = config.API_VERIFICAR
API_GUARDAR = config.API_GUARDAR
ARCHIVO_LOCAL = "datos_pendientes.json"

# Historial para media móvil
historial = []

def leer_tecla():
    for i, line in enumerate([L1, L2, L3, L4]):
        GPIO.output(line, GPIO.HIGH)
        for j, col in enumerate([C1, C2, C3, C4]):
            if GPIO.input(col) == GPIO.HIGH:
                GPIO.output(line, GPIO.LOW)
                time.sleep(0.3)
                return keys[i][j]
        GPIO.output(line, GPIO.LOW)
    return None

def verificar_codigo_offline(codigo):
    try:
        with open("vacas.json", "r") as archivo:
            data = json.load(archivo)
            for vaca in data.get("data", []):
                if vaca["identificador"].upper() == codigo.upper():
                    return True
    except:
        pass
    return False

def obtener_id_vaca(codigo):
    try:
        with open("vacas.json", "r") as archivo:
            data = json.load(archivo)
            for vaca in data.get("data", []):
                if vaca["identificador"].upper() == codigo.upper():
                    return int(vaca["id"])
    except:
        pass
    return 0

def verificar_codigo_en_api(codigo):
    try:
        response = requests.get(API_VERIFICAR, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for vaca in data:
                if vaca["identificador"].upper() == codigo.upper():
                    with open("vacas.json", "w") as archivo:
                        json.dump({"data": data}, archivo)
                    return "valido"
            return "invalido"
        else:
            return "error_api"
    except:
        if verificar_codigo_offline(codigo):
            return "valido"
        return "sin_conexion"

def enviar_datos_a_api(dato):
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(API_GUARDAR, json=dato, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"Enviado correctamente: {dato}")
            return True
        else:
            print(f"Error al enviar, status code: {re-sponse.status_code}")
            return False
    except Exception as e:
        print(f"Excepción al enviar datos: {e}")
        return False

def guardar_dato_localmente(dato):
    pendientes = []
    if os.path.exists(ARCHIVO_LOCAL):
        try:
            with open(ARCHIVO_LOCAL, "r") as f:
                pendientes = json.load(f)
        except:
            pendientes = []
    pendientes.append(dato)
    with open(ARCHIVO_LOCAL, "w") as f:
        json.dump(pendientes, f)
    print(f"Dato guardado localmente: {dato}")

def hay_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def intentar_enviar_datos_pendientes():
    if not os.path.exists(ARCHIVO_LOCAL):
        return

    with open(ARCHIVO_LOCAL, "r") as f:
        pendientes = json.load(f)

    nuevos_pendientes = []
    for dato in pendientes:
        print(f"Intentando enviar: {dato}")
        if not enviar_datos_a_api(dato):
            nuevos_pendientes.append(dato)

    if nuevos_pendientes:
        with open(ARCHIVO_LOCAL, "w") as f:
            json.dump(nuevos_pendientes, f)
    else:
        os.remove(ARCHIVO_LOCAL)
        print("Todos los datos pendientes enviados.")

def monitor_conexion():
    while True:
        if hay_internet():
            print("[Monitor] Conexión detectada. Intentando enviar datos pendientes...")
            intentar_enviar_datos_pendientes()
        time.sleep(30)

def obtener_peso_filtrado(n=5):
    global historial
    lectura = hx.get_units(5)
    historial.append(lectura)
    if len(historial) > n:
        historial = historial[-n:]
    return sum(historial) / len(historial)

# Iniciar hilo de monitoreo
threading.Thread(target=monitor_conexion, daemon=True).start()

try:
    lcd.lcd_string("Bienvenido al", lcddriver.LCD_LINE_1)
    lcd.lcd_string("Sistema UTM", lcddriver.LCD_LINE_2)
    time.sleep(3)
    lcd.clear()

    while True:
        codigo = ""
        lcd.lcd_string("Cod ganado:", lcddriver.LCD_LINE_1)
        lcd.lcd_string("", lcddriver.LCD_LINE_2)

        codigo_valido = False
        while not codigo_valido:
            tecla = leer_tecla()
            if tecla:
                if tecla == 'D':
                    codigo = codigo[:-1]
                elif tecla.isalnum() and len(codigo) < 4:
                    codigo += tecla
                elif tecla == '*':
                    lcd.clear()
                    lcd.lcd_string("Verificando...", lcddriv-er.LCD_LINE_1)
                    resultado = verificar_codigo_en_api(codigo)
                    if resultado == "valido":
                        lcd.lcd_string("Codigo valido", lcddri-ver.LCD_LINE_2)
                        codigo_valido = True
                    elif resultado == "invalido":
                        lcd.lcd_string("Codigo invalido", lcddri-ver.LCD_LINE_2)
                        codigo = ""
                    elif resultado == "sin_conexion":
                        lcd.lcd_string("Sin conexion", lcddriv-er.LCD_LINE_2)
                        codigo = ""
                    else:
                        lcd.lcd_string("Error API", lcddriver.LCD_LINE_2)
                        codigo = ""
                    time.sleep(2)
                    lcd.clear()
                lcd.lcd_string("Cod ganado:", lcddriver.LCD_LINE_1)
                lcd.lcd_string(codigo.ljust(16), lcddriver.LCD_LINE_2)

        lcd.lcd_string("Inicializando...", lcddriver.LCD_LINE_1)
        hx.tare()
        historial = []
        time.sleep(1)
        lcd.lcd_string("Base tareada", lcddriver.LCD_LINE_2)
        time.sleep(1)
        lcd.clear()

        lcd.lcd_string("Coloque recipiente", lcddriver.LCD_LINE_1)
        lcd.lcd_string("B = Guardar Tara", lcddriver.LCD_LINE_2)

        peso_recipiente = 0.0
        tara_hecha = False

        while not tara_hecha:
            tecla = leer_tecla()
            if tecla == 'B':
                peso_recipiente = obtener_peso_filtrado()
                litros_tara = peso_recipiente / 1000
                lcd.lcd_string("Tara guardada", lcddriver.LCD_LINE_1)
                lcd.lcd_string(f"{litros_tara:.3f} L", lcddriv-er.LCD_LINE_2)
                tara_hecha = True
                time.sleep(2)
                lcd.clear()

        lcd.lcd_string("Agregar contenido", lcddriver.LCD_LINE_1)
        lcd.lcd_string("C = Guardar y Enviar", lcddriver.LCD_LINE_2)

        while True:
            peso_actual = obtener_peso_filtrado()
            peso_neto = peso_actual - peso_recipiente
            if peso_neto < 0:
                peso_neto = 0.0
            litros = peso_neto / 1000
            lcd.lcd_string(f"Vol: {litros:.3f} L", lcddriver.LCD_LINE_1)

            tecla = leer_tecla()
            if tecla == 'C':
                litros_final = round(peso_neto / 1000, 3)
                fecha_hora_actual = time.strftime("%Y-%m-%d %H:%M:%S")
                id_vaca = obtener_id_vaca(codigo)

                dato = {
                    "id_vaca": id_vaca,
                    "identificador": codigo,
                    "prod_leche": litros_final,
                    "fecha_hora": fecha_hora_actual
                }

                lcd.lcd_string("Guardando datos...", lcddri-ver.LCD_LINE_1)
                if enviar_datos_a_api(dato):
                    lcd.lcd_string("Datos enviados OK", lcddri-ver.LCD_LINE_2)
                else:
                    lcd.lcd_string("Sin conexion", lcddriver.LCD_LINE_2)
                    guardar_dato_localmente(dato)

                time.sleep(3)
                lcd.clear()
                break

        lcd.lcd_string("Volumen final:", lcddriver.LCD_LINE_1)
        lcd.lcd_string(f"{litros_final:.3f} L", lcddriver.LCD_LINE_2)
        time.sleep(5)
        lcd.clear()

        lcd.lcd_string("Gracias por usar", lcddriver.LCD_LINE_1)
        lcd.lcd_string("el sistema!", lcddriver.LCD_LINE_2)
        time.sleep(3)
        lcd.clear()

except KeyboardInterrupt:
    lcd.lcd_string("Cancelado", lcddriver.LCD_LINE_1)
    GPIO.cleanup()
    lcd.clear()
except Exception as e:
    print(f"Error inesperado: {e}")
    GPIO.cleanup()
    lcd.clear()
