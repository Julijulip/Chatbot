import os
import random
from collections import Counter
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

from predict import analizar_texto, traducir_texto, generar_audio_traduccion

# ─── Configuración ──────────────────────────────────────

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ ERROR: Variable TELEGRAM_TOKEN no configurada")
    print("📌 Configuración:")
    print("   En PowerShell: $env:TELEGRAM_TOKEN='tu_token_aqui'")
    exit(1)

HISTORIAL_USUARIOS = {}

# ─── Datos ──────────────────────────────────────────────

INTERPRETACIONES = {
    "reclamo": [
        "📢 La persona se siente ignorada y reclama tu atención.",
        "😤 Hay frustración porque esperaba una respuesta y no llegó.",
        "💢 Percibe que la estás descuidando o ignorando.",
    ],
    "celos": [
        "😒 Siente inseguridad y teme que haya un tercero.",
        "🔍 Necesita confirmar que sigue siendo importante para ti.",
        "🤨 Desconfía de tus acciones o amistades.",
    ],
    "agresion": [
        "⚠️ Está usando palabras ofensivas o buscando herirte.",
        "🔥 El conflicto puede escalar si respondes con otro insulto.",
        "💥 Hay agresividad directa que debes frenar con calma.",
    ],
    "tristeza": [
        "😢 Está pasando por un momento difícil o de dolor.",
        "🫂 Necesita apoyo emocional y contención.",
        "💔 Hay vulnerabilidad, no lo ignores.",
    ],
    "manipulacion": [
        "🎭 Está usando culpa o condiciones para obtener lo que quiere.",
        "⛓️ Quiere presionarte emocionalmente para que actúes.",
        "⚠️ Ten cuidado con responder desde la culpa.",
    ],
    "control": [
        "🔒 Quiere saber todo lo que haces y con quién.",
        "👁️ Hay una necesidad excesiva de controlarte.",
        "📱 No confía plenamente en ti.",
    ],
    "ruptura": [
        "💔 Está considerando seriamente terminar la relación.",
        "😩 Hay agotamiento emocional acumulado.",
        "🚪 Quiere distancia o poner un punto final.",
    ],
    "desinteres": [
        "😐 No muestra interés en seguir la conversación.",
        "❄️ Hay distancia emocional o está ocupado.",
        "📉 Probablemente no quiere profundizar.",
    ],
    "inseguridad": [
        "😟 Tiene dudas sobre la relación o sobre sí mismo.",
        "🤔 Necesita reafirmación y seguridad.",
        "🌀 Busca calmar su ansiedad con respuestas claras.",
    ],
    "afecto": [
        "💕 Está expresando cariño y buenos sentimientos.",
        "🤗 Quiere acercarse y fortalecer el vínculo.",
        "🌸 Hay conexión emocional positiva.",
    ],
    "curiosidad": [
        "🤔 Tiene interés genuino en ti y tu vida.",
        "💬 Quiere iniciar o mantener una conversación.",
        "🔍 Busca conocer más sobre ti.",
    ],
    "normal": [
        "💬 Es una conversación cotidiana sin carga emocional.",
        "✅ No hay señales de conflicto ni urgencia.",
        "📝 Todo fluye con normalidad.",
    ],
}

SUGERENCIAS = {
    "reclamo": [
        "🗣️ Responde: 'Entiendo que te sientes ignorado, no fue mi intención. Hablemos.'",
        "⏸️ Reconoce su molestia antes de dar explicaciones: 'Tienes razón, no respondí rápido.'",
        "🤝 Pregunta: '¿Qué puedo hacer para que no te sientas así?'",
    ],
    "celos": [
        "🧠 Responde con calma: 'No hay nadie más, pero entiendo tu inseguridad.'",
        "💬 Valida su emoción: 'Veo que esto te preocupa, hablemos sin pelear.'",
        "🔐 Reafirma: 'Eres importante para mí. ¿Podemos hablar de esto tranquilos?'",
    ],
    "agresion": [
        "🌬️ No caigas en provocaciones. Di: 'No voy a responder si me hablas con ofensas.'",
        "🚫 Establece un límite claro: 'Si vas a insultar, mejor hablamos en otro momento.'",
        "⏰ Tómate distancia: 'Cuando estés más calmado hablamos con respeto.'",
    ],
    "tristeza": [
        "👥 Responde: 'Estoy aquí para ti. ¿Quieres hablar de lo que pasa?'",
        "💬 Muestra apoyo: 'Lamento que te sientas así, cuentas conmigo.'",
        "🤗 Ofrece compañía: '¿Necesitas desahogarte o prefieres distraerte?'",
    ],
    "manipulacion": [
        "🚩 No cedas por culpa. Di: 'No me gusta que me condiciones así.'",
        "🗣️ Marca límite: 'Si me quieres pedir algo, hazlo sin chantajes.'",
        "⚖️ Responde neutro: 'Te escucho, pero no voy a reaccionar desde la culpa.'",
    ],
    "control": [
        "🤝 Responde: 'Confío en ti y espero que tú confíes en mí.'",
        "📱 Marca espacio: 'Está bien que quieras saber, pero también necesito mi espacio.'",
        "🧘 Tranquiliza: 'No pasa nada, pero no puedo responder todo el tiempo.'",
    ],
    "ruptura": [
        "💬 Responde: 'Hablemos esto en persona, es importante.'",
        "🤔 Pide tiempo: 'No tomemos decisiones en caliente. Hablemos mañana.'",
        "🕊️ Si es firme: 'Lo respeto si es tu decisión, pero me duele.'",
    ],
    "desinteres": [
        "🧐 Pregunta: '¿Estás bien? Parece que no tienes ganas de hablar.'",
        "💬 Dale espacio: 'Cuando quieras hablar, aquí estoy.'",
        "⏸️ No insistas: 'Ok, hablamos cuando tengas tiempo.'",
    ],
    "inseguridad": [
        "🔍 Responde: 'Estoy contigo, no tienes nada que temer.'",
        "💬 Tranquiliza: 'Si algo te preocupa, pregúntame sin miedo.'",
        "📖 Reafirma: 'Me importas y no tengo nada que ocultar.'",
    ],
    "afecto": [
        "🌸 Corresponde: 'Yo también te quiero mucho ❤️'",
        "💌 Agradece: 'Qué bonito mensaje, gracias por tus palabras.'",
        "🎁 Sorprende: 'Me hiciste el día, te quiero igual.'",
    ],
    "curiosidad": [
        "🔍 Responde con entusiasmo: 'Todo bien, ¿y tú? Cuéntame.'",
        "💬 Aprovecha: 'Justo pensaba en ti. ¿Qué has hecho?'",
        "🌟 Sigue la conversación: 'Me alegra que preguntes, te cuento...'",
    ],
    "normal": [
        "👍 Responde con naturalidad: 'Todo bien, ¿y tú?'",
        "💬 Sigue la conversación: 'Qué bueno, seguimos hablando.'",
        "🌟 Mantén el tono: 'Genial, cualquier cosa me dices.'",
    ],
}

EMOJIS = {
    "reclamo": "😔", "celos": "😒", "agresion": "⚠️", "tristeza": "😢",
    "manipulacion": "🚩", "control": "🔒", "ruptura": "💔", "desinteres": "😶",
    "inseguridad": "😟", "afecto": "💕", "curiosidad": "🤔", "normal": "💬",
}

EMOJIS_EMOCION = {
    "positivo": "😊", "tristeza": "😢", "enojo": "😠", "sorpresa": "😲",
    "disgusto": "😖", "miedo": "😨", "neutral": "😐",
}

# ─── Funciones auxiliares ───────────────────────────────

def construir_barra(valor: int) -> str:
    bloques = valor // 10
    return "█" * bloques + "░" * (10 - bloques)

def obtener_texto(diccionario, clave, default="normal"):
    return random.choice(diccionario.get(clave, diccionario[default]))

def formatear_respuesta(datos: dict) -> str:
    bloque_traduccion = ""
    if datos.get("traduccion_es"):
        bloque_traduccion = f"🌐 *Traducción detectada:* _{datos['traduccion_es']}_\n"

    return (
        f"{datos['emoji_principal']} *Análisis del mensaje que te enviaron*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bloque_traduccion}"
        f"{datos['emoji_emocion']} *Emoción detectada:* {datos['emocion']} ({datos['confianza']}%)\n"
        f"🚩 *Toxicidad:* {datos['toxicidad']}\n"
        f"🧠 *Intención:* {datos['intencion']}\n"
        f"💔 *Ghosting:* {datos['ghosting_bar']} {datos['ghosting']}%\n"
        f"🔥 *Riesgo:* {datos['riesgo']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Qué significa:*\n{datos['interpretacion']}\n\n"
        f"💬 *Cómo responder:*\n{datos['sugerencia']}"
    )

# ─── Comandos ───────────────────────────────────────────

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_bienvenida = (
        "🤖 *¡Hola! Soy Openenglish IA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Puedo analizar cualquier mensaje que te envíen (en español o en otro idioma) y ayudarte a responder.\n\n"
        "📌 *¿Qué sé hacer?*\n"
        "• *Envíame cualquier texto:* Detecto emoción, toxicidad, riesgo, ghosting y te sugiero qué responder.\n"
        "• `/traducir <idioma> <texto>`: Traduzco frases cortas o párrafos largos y te envío un *audio con su pronunciación*.\n"
        "   _Ejemplo:_ `/traducir ingles Hola, ¿cómo estás hoy?`\n"
        "   _Ejemplo:_ `/traducir japones Muchas gracias`\n"
        "• `/resumen`: Te muestro un diagnóstico estadístico de los mensajes que has analizado hoy."
    )
    await update.message.reply_text(mensaje_bienvenida, parse_mode="Markdown")

async def comando_traducir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    partes = update.message.text.split(maxsplit=2)
    if len(partes) < 3:
        await update.message.reply_text(
            "⚠️ Uso correcto: /traducir <idioma> <texto>\n"
            "📌 Ejemplo: /traducir ingles Hola, ¿cómo estás hoy?"
        )
        return

    idioma_destino = partes[1]
    texto_a_traducir = partes[2]
    ruta_audio = None

    msg_espera = await update.message.reply_text("⏳ Traduciendo y generando audio...")

    try:
        traduccion, codigo = traducir_texto(texto_a_traducir, idioma_destino)
        respuesta = (
            f"🌐 Traducción ({codigo.upper()})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Original:\n{texto_a_traducir}\n\n"
            f"✅ Resultado:\n{traduccion}"
        )
        await msg_espera.edit_text(respuesta)

        try:
            ruta_audio = generar_audio_traduccion(traduccion[:500], codigo)
            with open(ruta_audio, "rb") as audio_file:
                await update.message.reply_voice(
                    voice=audio_file,
                    caption=f"🔊 Pronunciación en {idioma_destino.capitalize()}"
                )
        except Exception as audio_err:
            print(f"Aviso audio TTS: {audio_err}")

    except Exception as e:
        print(f"Error en comando_traducir: {e}")
        await msg_espera.edit_text(f"❌ Error al traducir a {idioma_destino}: {e}")
    finally:
        if ruta_audio and os.path.exists(ruta_audio):
            os.remove(ruta_audio)

async def comando_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    registros = HISTORIAL_USUARIOS.get(user_id, [])

    if not registros:
        await update.message.reply_text(
            "📊 Aún no has analizado ningún mensaje en esta sesión.\n"
            "Envíame al menos un mensaje de texto y luego usa `/resumen`.",
            parse_mode="Markdown"
        )
        return

    total = len(registros)
    promedio_ghosting = round(sum(r["ghosting"] for r in registros) / total)
    toxicos = sum(1 for r in registros if r["toxicidad"] == "si")
    emocion_top = Counter(r["emocion"] for r in registros).most_common(1)[0][0]
    intencion_top = Counter(r["intencion"] for r in registros).most_common(1)[0][0]

    reporte = (
        f"📊 *Resumen Estadístico de la Conversación*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 *Mensajes analizados:* {total}\n"
        f"🎭 *Emoción predominante:* {emocion_top.capitalize()}\n"
        f"🧠 *Intención más frecuente:* {intencion_top.capitalize()}\n"
        f"💔 *Promedio de Ghosting:* {construir_barra(promedio_ghosting)} {promedio_ghosting}%\n"
        f"🚩 *Mensajes tóxicos detectados:* {toxicos} de {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Este resumen ayuda a detectar patrones de comportamiento a lo largo de toda la charla._"
    )
    await update.message.reply_text(reporte, parse_mode="Markdown")

# ─── Handler principal ──────────────────────────────────

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        texto = update.message.text
        user_id = update.effective_user.id
        
        emocion, toxicidad, ghosting, riesgo, intencion, confianza, traduccion_es = analizar_texto(texto)
        
        HISTORIAL_USUARIOS.setdefault(user_id, []).append({
            "emocion": emocion,
            "toxicidad": toxicidad,
            "ghosting": ghosting,
            "intencion": intencion,
        })

        datos = {
            "emoji_principal": EMOJIS.get(intencion, "💬"),
            "emoji_emocion": EMOJIS_EMOCION.get(emocion, "😐"),
            "emocion": emocion.capitalize(),
            "confianza": confianza,
            "toxicidad": "🔴 Alta" if toxicidad == "si" else "🟢 Baja",
            "intencion": intencion.capitalize(),
            "ghosting": ghosting,
            "ghosting_bar": construir_barra(ghosting),
            "riesgo": riesgo,
            "interpretacion": obtener_texto(INTERPRETACIONES, intencion),
            "sugerencia": obtener_texto(SUGERENCIAS, intencion),
            "traduccion_es": traduccion_es,
        }
        
        respuesta = formatear_respuesta(datos)
        await update.message.reply_text(respuesta, parse_mode="Markdown")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("⚠️ Ocurrió un error al procesar el mensaje.")

# ─── Inicialización ─────────────────────────────────────

def main():
    print("🤖 Openenglish IA activo (análisis multilingüe, traducción y voz)...")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("traducir", comando_traducir))
    app.add_handler(CommandHandler("resumen", comando_resumen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("🟢 Bot corriendo... Esperando mensajes")
    app.run_polling()

if __name__ == "__main__":
    main()