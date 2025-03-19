import os
import telegram
import asyncio
from pycoingecko import CoinGeckoAPI
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
import requests

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

if not TOKEN or not CHAT_ID or not COINGECKO_API_KEY:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID o COINGECKO_API_KEY no están definidos en .env")

bot = telegram.Bot(token=TOKEN)
scheduler = AsyncIOScheduler()
cg = CoinGeckoAPI(api_key=COINGECKO_API_KEY)

# Configurar Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "¡El bot está funcionando correctamente!"

dolar_urls = {
    "💵 Dólar Blue": "https://dolarapi.com/v1/ambito/dolares/blue",
    "💰 Dólar Oficial": "https://dolarapi.com/v1/ambito/dolares/oficial",
    "💳 Dólar Tarjeta": "https://dolarapi.com/v1/ambito/dolares/tarjeta",
    "📈 Dólar Mayorista": "https://dolarapi.com/v1/ambito/dolares/mayorista",
}

stablecoins = ["tether", "usd-coin", "dai", "binance-usd"]
ultimo_dolar = {}
ultimo_cripto = {}
tendencias_enviadas = False

def obtener_cotizacion(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener datos de {url}: {e}")
        return None

def obtener_precio_stablecoins():
    try:
        return cg.get_price(ids=stablecoins, vs_currencies="usd")
    except Exception as e:
        print(f"❌ Error al obtener precios de stablecoins: {e}")
        return None

def obtener_tendencias_cripto():
    try:
        return cg.get_search_trending()
    except Exception as e:
        print(f"❌ Error al obtener tendencias de criptos: {e}")
        return None

async def enviar_mensaje(texto):
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

async def enviar_mensaje_inicial():
    await monitorear_dolar(inicial=True)
    await monitorear_stablecoins(inicial=True)
    await enviar_tendencias()

async def monitorear_dolar(inicial=False):
    global ultimo_dolar
    mensaje_dolar = "📊 *Cotización del Dólar en Argentina* 📊\n"
    cambios = False

    for nombre, url in dolar_urls.items():
        data = obtener_cotizacion(url)
        if data:
            compra, venta = data.get("compra"), data.get("venta")
            if inicial or nombre not in ultimo_dolar or ultimo_dolar[nombre] != (compra, venta):
                mensaje_dolar += f"\n{nombre}:\n💵 Compra: *{compra}*\n💲 Venta: *{venta}*"
                ultimo_dolar[nombre] = (compra, venta)
                cambios = True

    if cambios or inicial:
        mensaje_dolar += "\nℹ️ Información proporcionada por Ámbito Financiero."
        await enviar_mensaje(mensaje_dolar)

async def monitorear_stablecoins(inicial=False):
    global ultimo_cripto
    precios = obtener_precio_stablecoins()
    mensaje_crypto = "🚀 *Precios de Stablecoins* 🚀\n"
    cambios = False

    if precios:
        for cripto, datos in precios.items():
            precio_actual = datos.get("usd")
            precio_anterior = ultimo_cripto.get(cripto, None)

            if precio_anterior is not None:
                diferencia = precio_actual - precio_anterior
                simbolo_cambio = f" ({'+' if diferencia > 0 else ''}{diferencia:.2f})" if diferencia != 0 else ""
            else:
                simbolo_cambio = ""

            if inicial or simbolo_cambio:
                mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD*{simbolo_cambio}\n"
                ultimo_cripto[cripto] = precio_actual
                cambios = True

    if inicial or cambios:
        mensaje_crypto += "\nℹ️ Información proporcionada por CoinGecko."
        await enviar_mensaje(mensaje_crypto)

async def enviar_tendencias():
    global tendencias_enviadas
    if tendencias_enviadas:
        return  

    tendencias = obtener_tendencias_cripto()
    mensaje_tendencias = "📈 *Tendencias de criptomonedas* 📈\n"

    if tendencias:
        for idx, moneda in enumerate(tendencias.get("coins", []), start=1):
            nombre = moneda["item"]["name"]
            simbolo = moneda["item"]["symbol"].upper()
            mensaje_tendencias += f"🔸 *Top {idx}:* {nombre} ({simbolo})\n"

        mensaje_tendencias += "\nℹ️ Información proporcionada por CoinGecko."
        await enviar_mensaje(mensaje_tendencias)
        tendencias_enviadas = True  

async def main():
    await enviar_mensaje_inicial()  

    scheduler.add_job(monitorear_dolar, 'interval', minutes=5)
    scheduler.add_job(monitorear_stablecoins, 'interval', minutes=5)
    scheduler.add_job(enviar_tendencias, 'interval', days=1)  
    scheduler.start()

    print("🚀 Bot en ejecución 24/7 monitoreando cambios...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)).start()
    asyncio.run(main())
