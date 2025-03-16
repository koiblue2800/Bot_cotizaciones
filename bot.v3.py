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

# (Tu código para obtener cotizaciones, stablecoins, tendencias y enviar mensajes sigue igual)

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

