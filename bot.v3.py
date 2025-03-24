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
from prettytable import PrettyTable  # Para mostrar los datos en formato de tabla

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuración de zona horaria para Argentina
zona_argentina = pytz.timezone("America/Argentina/Buenos_Aires")

# Cargar variables de entorno
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

# Última cotización almacenada
ultimo_dolar = {}

# Función para extraer cotizaciones del dólar mediante web scraping
def obtener_cotizaciones_dolar():
    # Configuración de Selenium
    options = Options()
    options.add_argument('--headless')  # Ejecutar sin abrir el navegador
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # URL de Ámbito Financiero
    url = "https://www.ambito.com/"
    driver.get(url)

    # Esperar a que el contenido dinámico se cargue
    asyncio.sleep(5)

    # Extraer cotizaciones
    datos_dolar = {}

    try:
        secciones = driver.find_elements(By.CLASS_NAME, 'variation-max-min')

        for seccion in secciones:
            try:
                titulo = seccion.find_element(By.CSS_SELECTOR, 'h2.variation-max-min__title a span').text
                try:
                    compra = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__value.data-compra').text
                except:
                    compra = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__value').text
                try:
                    venta = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__value.data-venta').text
                except:
                    venta = "N/A"
                fecha = seccion.find_element(By.CSS_SELECTOR, 'span.variation-max-min__date-time').text

                datos_dolar[titulo] = {"compra": compra, "venta": venta, "fecha": fecha}

            except Exception as e:
                logging.error(f"No se pudieron extraer datos de una sección: {e}")

    except Exception as e:
        logging.error(f"Error al extraer datos: {e}")
    finally:
        driver.quit()

    return datos_dolar

async def monitorear_dolar():
    global ultimo_dolar
    mensaje_dolar = "📊 *Cotización del Dólar en Argentina* 📊\n"
    cambios = False

    datos = obtener_cotizaciones_dolar()
    for titulo, valores in datos.items():
        compra = valores["compra"]
        venta = valores["venta"]
        fecha = valores["fecha"]

        # Verifica si es la primera ejecución o si hubo cambios
        if titulo not in ultimo_dolar or ultimo_dolar[titulo] != (compra, venta, fecha):
            mensaje_dolar += f"\n💵 {titulo}:\n💳 Compra: *{compra}*\n💰 Venta: *{venta}*\n🕒 Actualización: *{fecha}*"
            ultimo_dolar[titulo] = (compra, venta, fecha)
            cambios = True

    # Enviar mensaje inicial o si hay cambios
    if cambios or not ultimo_dolar:
        await enviar_mensaje(mensaje_dolar)

async def enviar_mensaje(texto):
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
        logging.info("✅ Mensaje enviado correctamente.")
    except Exception as e:
        logging.error(f"❌ Error al enviar mensaje: {e}")

async def main():
    try:
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
