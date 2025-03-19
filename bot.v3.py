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
