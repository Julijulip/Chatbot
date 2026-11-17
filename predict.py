# predict.py - Versión final con detección de idioma precisa, filtro de ofensas, traducción por bloques y voz (TTS)
import os
import time
import tempfile
from gtts import gTTS
from pysentimiento import create_analyzer
from deep_translator import MyMemoryTranslator, GoogleTranslator

# ─── Modelos preentrenados ─────────────────────────

print("🔄 Cargando modelos de pysentimiento...")
emotion_analyzer = create_analyzer(task="emotion", lang="es")
hate_analyzer = create_analyzer(task="hate_speech", lang="es")
print("✅ Modelos cargados correctamente")

# ─── Diccionario de idiomas soportados ───────────────

IDIOMAS = {
    "español": "es-ES", "espanol": "es-ES", "es": "es-ES", "spanish": "es-ES",
    "inglés": "en-US", "ingles": "en-US", "en": "en-US", "english": "en-US",
    "francés": "fr-FR", "frances": "fr-FR", "fr": "fr-FR", "french": "fr-FR",
    "alemán": "de-DE", "aleman": "de-DE", "de": "de-DE", "german": "de-DE",
    "portugués": "pt-PT", "portugues": "pt-PT", "pt": "pt-PT", "portuguese": "pt-PT",
    "italiano": "it-IT", "it": "it-IT", "italian": "it-IT",
    "japonés": "ja-JP", "japones": "ja-JP", "ja": "ja-JP", "japanese": "ja-JP",
    "coreano": "ko-KR", "ko": "ko-KR", "korean": "ko-KR",
    "chino": "zh-CN", "zh": "zh-CN", "chinese": "zh-CN",
    "ruso": "ru-RU", "ru": "ru-RU", "russian": "ru-RU",
    "árabe": "ar-SA", "arabe": "ar-SA", "ar": "ar-SA", "arabic": "ar-SA",
    "holandés": "nl-NL", "holandes": "nl-NL", "nl": "nl-NL", "dutch": "nl-NL",
}

def detectar_idioma_origen(texto: str, destino: str) -> str:
    """Detecta si el texto contiene palabras en inglés; de lo contrario asume español."""
    palabras_en = {
        "the", "is", "are", "you", "why", "what", "how", "don't", "do",
        "not", "my", "me", "i", "hello", "hi", "thanks", "answer", "love",
        "miss", "hate", "sorry", "please", "because", "when", "where", "who",
        "your", "ugly", "stupid", "leave", "stop", "want", "need", "good", "bad"
    }
    tokens = set(
        texto.lower()
        .replace("?", "")
        .replace("!", "")
        .replace(",", "")
        .replace(".", "")
        .split()
    )
    if tokens & palabras_en:
        return "en-US"
    return "es-ES"

def dividir_en_bloques(texto: str, max_chars: int = 250) -> list[str]:
    """Limpia saltos de línea y divide textos largos en bloques cortos de máximo 250 caracteres."""
    texto_limpio = " ".join(texto.split())
    palabras = texto_limpio.split(" ")
    bloques = []
    actual = ""
    for palabra in palabras:
        if len(actual) + len(palabra) + 1 <= max_chars:
            actual = f"{actual} {palabra}".strip()
        else:
            if actual:
                bloques.append(actual)
            actual = palabra
    if actual:
        bloques.append(actual)
    return bloques

def traducir_texto(texto: str, idioma_destino: str) -> tuple[str, str]:
    clave = idioma_destino.strip().lower()
    if clave not in IDIOMAS and "-" not in clave and len(clave) != 2:
        raise ValueError(f"Idioma no soportado: {idioma_destino}")

    codigo = IDIOMAS.get(clave, clave)
    origen = detectar_idioma_origen(texto, codigo)

    if origen == codigo:
        return texto, codigo.split("-")[0]

    bloques = dividir_en_bloques(texto, max_chars=250)
    traducciones = []

    for i, bloque in enumerate(bloques):
        if i > 0:
            time.sleep(0.4)
        try:
            parte = MyMemoryTranslator(source=origen, target=codigo).translate(bloque)
            traducciones.append(parte)
        except Exception as e1:
            print(f"MyMemory falló en bloque {i}: {e1}")
            codigo_corto = codigo.split("-")[0] if codigo != "zh-CN" else "zh-CN"
            parte = GoogleTranslator(source="auto", target=codigo_corto).translate(bloque)
            traducciones.append(parte)

    return " ".join(traducciones), codigo.split("-")[0]

def generar_audio_traduccion(texto: str, codigo_idioma: str) -> str:
    """
    Convierte el texto traducido a un archivo de audio MP3 temporal usando gTTS
    y devuelve la ruta del archivo generado.
    """
    lang_tts = "zh-CN" if codigo_idioma.lower().startswith("zh") else codigo_idioma.split("-")[0]
    tts = gTTS(text=texto, lang=lang_tts, slow=False)
    archivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    archivo_temp.close()
    tts.save(archivo_temp.name)
    return archivo_temp.name

# ─── Intención (reglas mejoradas) ─────────────────────

INSULTOS_Y_OFENSAS = [
    "odio", "estúpido", "estupido", "idiota", "imbécil", "imbecil",
    "estúpida", "estupida", "mierda", "qué asco", "que asco",
    "feo", "fea", "horrible", "tonto", "tonta", "bobo", "boba",
    "ridículo", "ridiculo", "fastidioso", "fastidiosa", "insoportable",
    "payaso", "basura", "inútil", "inutil", "patético", "patetico",
    "cállate", "callate", "lárgate", "largate", "maldito", "maldita"
]

def detectar_intencion(texto):
    texto = texto.lower()
    
    if any(palabra in texto for palabra in ["te quiero", "te amo", "me gustas", "te extraño", "te necesito", "te adoro", "te quiero mucho"]):
        return "afecto"
    elif any(palabra in texto for palabra in ["por qué no respondes", "me ignoras", "no contestas", "por qué tardas", "por qué demoras", "no me escribes", "por qué no me respondes"]):
        return "reclamo"
    elif any(palabra in texto for palabra in ["con quién", "quién es", "te veo con", "andabas con", "quién te escribió", "quién te habla"]):
        return "celos"
    elif any(palabra in texto for palabra in INSULTOS_Y_OFENSAS):
        return "agresion"
    elif any(palabra in texto for palabra in ["terminar", "dejar", "no quiero seguir", "acabó", "se acabó", "hasta aquí", "se terminó"]):
        return "ruptura"
    elif any(palabra in texto for palabra in ["si me quisieras", "deberías", "nunca haces", "siempre igual", "como siempre", "si realmente me quisieras"]):
        return "manipulacion"
    elif any(palabra in texto for palabra in ["dónde estás", "qué haces", "con quién hablas", "dime la verdad", "ubicación", "envía ubicación"]):
        return "control"
    elif any(palabra in texto for palabra in ["ok", "vale", "ah", "ya", "como digas", "da igual", "me da igual", "jaja", "jeje", "ok ok"]):
        return "desinteres"
    elif any(palabra in texto for palabra in ["qué tal", "cómo estás", "qué haces", "cómo te va", "en qué andas", "qué cuentas"]):
        return "curiosidad"
    elif any(palabra in texto for palabra in ["triste", "deprimido", "mal", "solo", "soledad", "llorar", "me siento mal"]):
        return "tristeza"
    else:
        return "normal"

# ─── Ghosting ─────────────────────────────────────────

def calcular_ghosting(texto, intencion, emocion):
    score = 0
    texto = texto.lower()
    
    if len(texto) <= 5:
        score += 35
    if len(texto.split()) == 1:
        score += 25
    if any(palabra in texto for palabra in ["ok", "vale", "ah", "ya", "luego", "ocupado", "ahora no", "después", "mañana", "ahora no puedo"]):
        score += 30
    
    if intencion == "desinteres":
        score += 35
    elif intencion == "reclamo":
        score += 15
    elif intencion == "afecto":
        score -= 25
    
    if emocion in ["sadness", "anger", "fear", "disgust"]:
        score += 10
    elif emocion in ["joy", "surprise"]:
        score -= 15
    
    return max(0, min(score, 95))

# ─── Calcular riesgo ───────────────────────────────────

def calcular_riesgo(hate_result, intencion, emocion):
    if hate_result.output == "hateful" or hate_result.output == "targeted":
        return "🔴 Alto"
    elif intencion == "agresion":
        return "🔴 Alto"
    elif intencion in ["celos", "reclamo", "ruptura", "manipulacion", "control"]:
        return "🟡 Medio"
    elif emocion in ["anger", "disgust"]:
        return "🟡 Medio"
    else:
        return "🟢 Bajo"

# ─── Mapear emociones ───────────────────────────────────

def mapear_emocion(emocion_raw):
    emocion_map = {
        'joy': 'positivo',
        'sadness': 'tristeza',
        'anger': 'enojo',
        'surprise': 'sorpresa',
        'disgust': 'disgusto',
        'fear': 'miedo',
        'neutral': 'neutral'
    }
    return emocion_map.get(emocion_raw, 'neutral')

# ─── Función principal (multilingüe) ───────────────────

def analizar_texto(texto):
    try:
        texto_para_analizar = texto
        traduccion_es = None
        try:
            if detectar_idioma_origen(texto, "es-ES") == "en-US":
                traducido, _ = traducir_texto(texto, "español")
                if traducido and traducido.strip().lower() != texto.strip().lower():
                    texto_para_analizar = traducido
                    traduccion_es = traducido
        except Exception as e:
            print(f"Aviso traducción interna: {e}")

        emocion_pred = emotion_analyzer.predict(texto_para_analizar)
        hate_pred = hate_analyzer.predict(texto_para_analizar)
        
        emocion_raw = emocion_pred.output
        emocion = mapear_emocion(emocion_raw)
        intencion = detectar_intencion(texto_para_analizar)

        es_ofensivo = hate_pred.output in ["hateful", "targeted"] or intencion == "agresion"
        toxicidad = "si" if es_ofensivo else "no"
        if intencion == "agresion" and emocion == "neutral":
            emocion = "disgusto"

        ghosting = calcular_ghosting(texto_para_analizar, intencion, emocion_raw)
        riesgo = calcular_riesgo(hate_pred, intencion, emocion_raw)
        confianza = max(emocion_pred.probas.values())
        
        return emocion, toxicidad, ghosting, riesgo, intencion, int(confianza * 100), traduccion_es
    
    except Exception as e:
        print(f"Error en analizar_texto: {e}")
        return "neutral", "no", 0, "🟢 Bajo", "normal", 50, None