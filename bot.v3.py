import os
import telegram
import asyncio
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
from datetime import datetime, timedelta
import pytz
import logging

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuración de zona horaria para Argentina
zona_argentina = pytz.timezone("America/Argentina/Buenos_Aires")
ultimo_envio_tendencias = None
ultimo_envio_stablecoins = None

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

# URLs para monitorear el dólar
dolar_urls = {
"💵 Dólar Blue": "https://dolarapi.com/v1/ambito/dolares/blue",
"💰 Dólar Oficial": "https://dolarapi.com/v1/ambito/dolares/oficial", 
"💳 Dólar Tarjeta": "https://dolarapi.com/v1/ambito/dolares/tarjeta",
"📈 Dólar Mayorista": "https://dolarapi.com/v1/ambito/dolares/mayorista",
}

# Configuración para stablecoins
stablecoins = ["tether", "usd-coin", "dai", "binance-usd"]
ultimo_dolar = {}
ultimo_cripto = {}

# Función para obtener cotizaciones
def obtener_cotizacion(url):
try:
response = requests.get(url, timeout=10)
response.raise_for_status()
return response.json()
except requests.RequestException as e:
        print(f"❌ Error al obtener datos de {url}: {e}")
        logging.error(f"❌ Error al obtener datos de {url}: {e}")
return None

def obtener_precio_stablecoins():
@@ -60,40 +67,36 @@
try:
response = requests.get(url, params=params, timeout=10)
if response.status_code == 429:
            print("Límite de tasa excedido. Esperando...")
            logging.warning("Límite de tasa excedido. Esperando...")
return None
response.raise_for_status()
return response.json()
except requests.RequestException as e:
        print(f"❌ Error al obtener precios de stablecoins: {e}")
        logging.error(f"❌ Error al obtener precios de stablecoins: {e}")
return None

def obtener_tendencias_cripto():
url = "https://api.coingecko.com/api/v3/search/trending"
try:
response = requests.get(url, timeout=10)
if response.status_code == 429:
            print("Límite de tasa excedido. Esperando...")
            logging.warning("Límite de tasa excedido. Esperando...")
return None
response.raise_for_status()
return response.json()
except requests.RequestException as e:
        print(f"❌ Error al obtener tendencias de criptos: {e}")
        logging.error(f"❌ Error al obtener tendencias de criptos: {e}")
return None

async def enviar_mensaje(texto):
try:
async with bot:
await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
        logging.info("✅ Mensaje enviado correctamente.")
except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

async def enviar_mensaje_inicial():
    await monitorear_dolar(inicial=True)
    await monitorear_stablecoins(inicial=True)
    await enviar_tendencias()
        logging.error(f"❌ Error al enviar mensaje: {e}")

async def monitorear_dolar(inicial=False):
async def monitorear_dolar():
global ultimo_dolar
mensaje_dolar = "📊 *Cotización del Dólar en Argentina* 📊\n"
cambios = False
@@ -102,55 +105,43 @@
data = obtener_cotizacion(url)
if data:
compra, venta = data.get("compra"), data.get("venta")
            if inicial or nombre not in ultimo_dolar or ultimo_dolar[nombre] != (compra, venta):
            if nombre not in ultimo_dolar or ultimo_dolar[nombre] != (compra, venta):
mensaje_dolar += f"\n{nombre}:\n💵 Compra: *{compra}*\n💲 Venta: *{venta}*"
ultimo_dolar[nombre] = (compra, venta)
cambios = True

    if cambios or inicial:
    if cambios:
mensaje_dolar += "\nℹ️ Información proporcionada por Ámbito Financiero."
await enviar_mensaje(mensaje_dolar)

async def monitorear_stablecoins(inicial=False):
async def monitorear_stablecoins():
global ultimo_cripto, ultimo_envio_stablecoins
precios = obtener_precio_stablecoins()
mensaje_crypto = "🚀 *Precios de Stablecoins* 🚀\n"
cambios = False
    umbral_cambio_stablecoins = 0.5  # Umbral del 0.5%

    # Obtener hora actual en Argentina
    ahora_arg = datetime.now(zona_argentina)

if precios:
for cripto, datos in precios.items():
precio_actual = datos.get("usd")
precio_anterior = ultimo_cripto.get(cripto, {}).get("precio")

            if precio_anterior is not None:
                variacion = abs(precio_actual - precio_anterior) / precio_anterior * 100
                if variacion >= umbral_cambio_stablecoins:
                    simbolo_cambio = f" ({'+' if precio_actual > precio_anterior else ''}{precio_actual - precio_anterior:.2f})"
                    mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD*{simbolo_cambio} (Variación: {variacion:.2f}%)\n"
                    ultimo_cripto[cripto] = {"precio": precio_actual}
                    cambios = True
            else:
                # Inicialización de los precios
            if precio_anterior is None or abs(precio_actual - precio_anterior) / precio_anterior * 100 >= 0.5:
mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD*\n"
ultimo_cripto[cripto] = {"precio": precio_actual}
cambios = True

    if inicial or cambios or (ultimo_envio_stablecoins is None or ahora_arg - ultimo_envio_stablecoins >= timedelta(days=1)):
    if cambios:
mensaje_crypto += "\nℹ️ Información proporcionada por CoinGecko."
await enviar_mensaje(mensaje_crypto)
        ultimo_envio_stablecoins = ahora_arg
        ultimo_envio_stablecoins = datetime.now(zona_argentina)

async def enviar_tendencias():
global ultimo_envio_tendencias
ahora_arg = datetime.now(zona_argentina)

    # Asegurar envío diario
    logging.info(f"Intentando enviar tendencias a las {ahora_arg}. Último envío: {ultimo_envio_tendencias}")
if ultimo_envio_tendencias and ahora_arg - ultimo_envio_tendencias < timedelta(days=1):
        return  
        logging.warning("Ya se enviaron las tendencias en las últimas 24 horas. No se enviará nuevamente.")
        return

tendencias = obtener_tendencias_cripto()
mensaje_tendencias = "📈 *Tendencias de criptomonedas* 📈\n"
@@ -168,20 +159,17 @@

async def main():
try:
        await enviar_mensaje_inicial()
        
scheduler.add_job(monitorear_dolar, 'interval', minutes=5)
scheduler.add_job(monitorear_stablecoins, 'interval', minutes=5)
        scheduler.add_job(enviar_tendencias, 'cron', hour=9, timezone="America/Argentina/Buenos_Aires")  # Envía a las 9 AM
        scheduler.add_job(enviar_tendencias, 'cron', hour=0, timezone="America/Argentina/Buenos_Aires")  # Cambiado a las 12 AM
scheduler.start()

        print("🚀 Bot en ejecución 24/7 monitoreando cambios...")
        logging.info("🚀 Bot iniciado y monitoreando tareas.")
while True:
await asyncio.sleep(1)
except Exception as e:
        print(f"Error en main: {e}")
        logging.error(f"Error en main: {e}")

if __name__ == "__main__":
import threading
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)).start()
asyncio.run(main())
