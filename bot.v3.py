import os
import requests
import telegram
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están definidos en .env")

bot = telegram.Bot(token=TOKEN)
scheduler = AsyncIOScheduler()

# Configurar Flask para mantener un servidor activo
app = Flask(__name__)

@app.route("/")
def home():
    return "¡El bot está funcionando correctamente!"

# URLs de cotización del dólar
dolar_urls = {
    "💵 Dólar Blue": "https://dolarapi.com/v1/ambito/dolares/blue",
    "💰 Dólar Oficial": "https://dolarapi.com/v1/ambito/dolares/oficial",
    "💳 Dólar Tarjeta": "https://dolarapi.com/v1/ambito/dolares/tarjeta",
    "📈 Dólar Mayorista": "https://dolarapi.com/v1/ambito/dolares/mayorista",
}

# Criptomonedas a monitorear
stablecoins = ["tether", "usd-coin", "dai", "binance-usd"]

# Diccionarios para guardar valores previos
ultimo_dolar = {}
ultimo_cripto = {}
tendencias_enviadas = False  # Para enviar las tendencias solo 1 vez al inicio

def obtener_cotizacion(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener datos de {url}: {e}")
        return None

def obtener_precio_cripto():
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(stablecoins)}&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener precios de criptos: {e}")
        return None

def obtener_tendencias_cripto():
    url = "https://api.coingecko.com/api/v3/search/trending"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error al obtener tendencias de criptos: {e}")
        return None

async def enviar_mensaje(texto):
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

async def enviar_mensaje_inicial():
    """Envía un mensaje inicial con todas las cotizaciones y tendencias"""
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
    precios = obtener_precio_cripto()
    mensaje_crypto = "🚀 *Precios de Stablecoins* 🚀\n"
    cambios = False

    if precios:
        for cripto, datos in precios.items():
            precio_actual = datos.get("usd")
            precio_anterior = ultimo_cripto.get(cripto, None)

            if precio_anterior is not None:
                diferencia = precio_actual - precio_anterior
                if diferencia > 0:
                    simbolo_cambio = f"+{diferencia:.2f}"
                elif diferencia < 0:
                    simbolo_cambio = f"{diferencia:.2f}"
                else:
                    simbolo_cambio = ""

                if simbolo_cambio or inicial:
                    mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD* ({simbolo_cambio})\n"
            else:
                mensaje_crypto += f"🔹 *{cripto.upper()}*: *${precio_actual} USD*\n"
                ultimo_cripto[cripto] = precio_actual
                cambios = True

    if cambios or inicial:
        mensaje_crypto += "\nℹ️ Información proporcionada por CoinGecko."
        await enviar_mensaje(mensaje_crypto)

async def enviar_tendencias():
    global tendencias_enviadas
    if tendencias_enviadas:
        return  # No enviar de nuevo si ya se enviaron una vez

    tendencias = obtener_tendencias_cripto()
    mensaje_tendencias = "📈 *Tendencias de criptomonedas* 📈\n"

    if tendencias:
        for idx, moneda in enumerate(tendencias.get("coins", []), start=1):
            nombre = moneda["item"]["name"]
            simbolo = moneda["item"]["symbol"].upper()
            mensaje_tendencias += f"🔸 *Top {idx}:* {nombre} ({simbolo})\n"

        mensaje_tendencias += "\nℹ️ Información proporcionada por CoinGecko."
        await enviar_mensaje(mensaje_tendencias)
        tendencias_enviadas = True  # Marcar como enviadas para que no se repitan

async def main():
    """Función principal que inicia el bot y programa las actualizaciones"""
    await enviar_mensaje_inicial()  # Enviar el mensaje inicial

    scheduler.add_job(monitorear_dolar, 'interval', minutes=5)
    scheduler.add_job(monitorear_stablecoins, 'interval', minutes=5)
    scheduler.add_job(enviar_tendencias, 'interval', days=1)  # Enviar tendencias una vez al día
    scheduler.start()

    print("🚀 Bot en ejecución 24/7 monitoreando cambios...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Ejecutar Flask y el bot en paralelo
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)).start()
    asyncio.run(main())
