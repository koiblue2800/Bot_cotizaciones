import os
import telegram
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
from datetime import datetime, timedelta
import pytz
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from prettytable import PrettyTable
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Zona horaria para Argentina
zona_argentina = pytz.timezone("America/Argentina/Buenos_Aires")

# Variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están definidos en .env")

bot = telegram.Bot(token=TOKEN)
scheduler = AsyncIOScheduler()

# Configurar Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "¡El bot está funcionando correctamente!"

ultimo_dolar = {}
ultimo_cripto = {}
ultimo_envio_stablecoins = None
ultimo_envio_tendencias = None

# Función para enviar mensajes
async def enviar_mensaje(texto):
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
        logging.info("✅ Mensaje enviado correctamente.")
    except Exception as e:
        logging.error(f"❌ Error al enviar mensaje: {e}")

# Web scraping para obtener cotizaciones del dólar
def obtener_cotizaciones_dolar():
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "https://www.ambito.com/"
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'variation-max-min')))
    datos_dolar = {}
    try:
        secciones = driver.find_elements(By.CLASS_NAME, 'variation-max-min')
        for seccion in secciones:
            try:
                titulo = seccion.find_element(By.CSS_SELECTOR, 'h2.variation-max-min__title a span').text
                compra = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__value.data-compra').text
                venta = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__value.data-venta').text
                fecha = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__date-time').text
                datos_dolar[titulo] = {"compra": compra, "venta": venta, "fecha": fecha}
            except Exception as e:
                logging.error(f"No se pudieron extraer datos: {e}")
    except Exception as e:
        logging.error(f"Error al obtener cotizaciones: {e}")
    finally:
        driver.quit()
    return datos_dolar

async def monitorear_dolar():
    global ultimo_dolar
    mensaje_dolar = "📊 *Cotización del Dólar en Argentina* 📊\n"
    cambios = False
    datos = obtener_cotizaciones_dolar()
    logging.info(f"Datos obtenidos del dólar: {datos}")
    for titulo, valores in datos.items():
        compra = valores["compra"]
        venta = valores["venta"]
        fecha = valores["fecha"]
        if titulo not in ultimo_dolar or ultimo_dolar[titulo] != (compra, venta, fecha):
            mensaje_dolar += f"\n💵 {titulo}:\n💳 Compra: *{compra}*\n💰 Venta: *{venta}*\n🕒 Actualización: *{fecha}*"
            ultimo_dolar[titulo] = (compra, venta, fecha)
            cambios = True
    if cambios or not ultimo_dolar:
        await enviar_mensaje(mensaje_dolar)

# Función para monitorear stablecoins
async def monitorear_stablecoins():
    global ultimo_cripto, ultimo_envio_stablecoins
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "tether,usd-coin,dai,binance-usd", "vs_currencies": "usd"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        precios = response.json()
        logging.info(f"Precios obtenidos de stablecoins: {precios}")
        mensaje_crypto = "🚀 *Precios de Stablecoins* 🚀\n"
        cambios = False
        for cripto, datos in precios.items():
            precio_actual = datos.get("usd")
            if cripto not in ultimo_cripto or abs(precio_actual - ultimo_cripto.get(cripto, {}).get("precio", 0)) / precio_actual >= 0.005:
                mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD*\n"
                ultimo_cripto[cripto] = {"precio": precio_actual}
                cambios = True
        if cambios:
            await enviar_mensaje(mensaje_crypto)
            ultimo_envio_stablecoins = datetime.now(zona_argentina)
    except Exception as e:
        logging.error(f"❌ Error al obtener precios de stablecoins: {e}")

# Función para enviar tendencias de criptos
async def enviar_tendencias():
    global ultimo_envio_tendencias
    url = "https://api.coingecko.com/api/v3/search/trending"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        tendencias = response.json()
        logging.info(f"Tendencias obtenidas: {tendencias}")
        mensaje_tendencias = "📈 *Tendencias de criptomonedas* 📈\n"
        for idx, moneda in enumerate(tendencias.get("coins", [])[:7], start=1):
            item = moneda.get("item", {})
            nombre = item.get("name", "N/A")
            simbolo = item.get("symbol", "N/A").upper()
            mensaje_tendencias += f"🔸 *Top {idx}:* {nombre} ({simbolo})\n"
        if tendencias:
            await enviar_mensaje(mensaje_tendencias)
            ultimo_envio_tendencias = datetime.now(zona_argentina)
    except Exception as e:
        logging.error(f"❌ Error al obtener tendencias: {e}")

async def main():
    try:
        # Enviar mensaje inicial
        await enviar_mensaje("🚀 Bot iniciado y monitoreando tareas.")

        scheduler.add_job(enviar_tendencias, 'interval', minutes=60)
        scheduler.add_job(monitorear_stablecoins, 'interval', minutes=10)
        scheduler.add_job(monitorear_dolar, 'interval', minutes=5)
        scheduler.start()
        logging.info("🚀 Bot iniciado y monitoreando tareas.")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logging.error(f"Error en main: {e}")

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)).start()
    asyncio.run(main())
