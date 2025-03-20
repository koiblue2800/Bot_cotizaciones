import os
import telegram
import asyncio
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

if not TOKEN or not CHAT_ID or not COINGECKO_API_KEY:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID o COINGECKO_API_KEY no están definidos en .env")

bot = telegram.Bot(token=TOKEN)
scheduler = AsyncIOScheduler()

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
ultimo_cripto = {}
tendencias_enviadas = False

# Obtener precios de stablecoins
def obtener_precio_stablecoins():
    url = "https://pro-api.coingecko.com/api/v3/simple/price"
    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}
    params = {
        "ids": ",".join(stablecoins),
        "vs_currencies": "usd"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener precios de stablecoins: {e}")
        return None

# Obtener tendencias de criptomonedas
def obtener_tendencias_cripto():
    url = "https://pro-api.coingecko.com/api/v3/search/trending"
    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener tendencias de criptomonedas: {e}")
        return None

# Enviar mensaje al chat
async def enviar_mensaje(texto):
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

# Monitorear y enviar precios de stablecoins
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

# Enviar tendencias de criptomonedas
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

# Función principal
async def main():
    await monitorear_dolar(inicial=True)  # Mantener lógica original del dólar
    await monitorear_stablecoins(inicial=True)  # Enviar precios iniciales de stablecoins
    await enviar_tendencias()  # Enviar tendencias iniciales

    # Programar tareas periódicas
    scheduler.add_job(monitorear_dolar, 'interval', minutes=5)
    scheduler.add_job(monitorear_stablecoins, 'interval', minutes=5)
    scheduler.add_job(enviar_tendencias, 'interval', days=1)  
    scheduler.start()

    print("🚀 Bot en ejecución 24/7 monitoreando cambios...")
    while True:
        await asyncio.sleep(1)

# Iniciar la aplicación y el bot
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)).start()
    asyncio.run(main())
