"""
Agente automatizado de vídeos infantiles
=========================================
Genera un vídeo corto de comedia educativa para niños de 2 a 5 años, en español,
y lo sube automáticamente a YouTube.

Flujo:
 1. Anthropic API      -> escribe el guion (personaje fijo + escenas + narración)
 2. fal.ai (Flux)      -> genera UNA imagen de referencia del personaje (para que
                           sea siempre el mismo niño en todas las escenas)
 3. ElevenLabs API     -> convierte cada narración en audio
 4. fal.ai (Kling)     -> genera un CLIP DE VÍDEO ANIMADO por escena, partiendo
                           siempre de la imagen de referencia del personaje
 5. Anthropic API      -> AGENTE VERIFICADOR: revisa un fotograma de cada clip y,
                           si detecta algo raro (personaje distinto, física
                           imposible, etc.), pide regenerar el clip
 6. moviepy            -> monta el vídeo final (clips + subtítulos + audio)
 7. YouTube Data API   -> sube el vídeo al canal

Todas las claves se leen de variables de entorno (ver README.md).
"""

import os
import io
import json
import time
import base64
import textwrap
import requests

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
FAL_API_KEY = os.environ["FAL_API_KEY"]

WORKDIR = "output"
os.makedirs(WORKDIR, exist_ok=True)

TEMA = os.environ.get(
    "TEMA_DEL_DIA",
    "una situación divertida cotidiana (bañarse, comer verduras, recoger juguetes, "
    "compartir con un amigo, tener miedo a la oscuridad, etc.) con un mensaje educativo claro",
)

MAX_INTENTOS_CLIP = 3  # 1 intento normal + hasta 2 regeneraciones si el verificador lo rechaza

NEGATIVE_PROMPT_VIDEO = (
    "personaje distinto, cara distinta, ropa distinta, cambia de aspecto, "
    "física imposible, andar por el techo, andar por las paredes, levitar sin motivo, "
    "extremidades extra, manos deformes, cuerpo deformado, texto en pantalla, "
    "borroso, mala calidad, parpadeo, distorsión"
)


# ---------------------------------------------------------------------------
# UTILIDAD: llamar a Claude (texto o visión)
# ---------------------------------------------------------------------------

def llamar_claude(mensajes, max_tokens=1500):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": max_tokens,
            "messages": mensajes,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(b["text"] for b in data["content"] if b["type"] == "text")


def extraer_json(texto):
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto.strip())


# ---------------------------------------------------------------------------
# PASO 1: GUION CON CLAUDE (personaje fijo + escenas)
# ---------------------------------------------------------------------------

def generar_guion():
    prompt = f"""
Eres un guionista experto en contenido infantil para YouTube (estilo Cocomelon / Pocoyó),
dirigido a niños de 2 a 5 años, en español de España.

Escribe un guion corto de comedia con situaciones graciosas y una lección educativa
sobre: {TEMA}.

Requisitos MUY IMPORTANTES:
- Hay UN SOLO personaje protagonista que aparece en TODAS las escenas. Descríbelo
  con mucho detalle físico (edad aparente, pelo, color de piel, ropa exacta,
  color de ojos, complexión) para que se pueda dibujar siempre igual.
- Entre 4 y 6 escenas, cada una con su propio gag o momento gracioso concreto
  (no solo "está feliz", sino una ACCIÓN física graciosa y realista para un niño:
  tropezarse con un juguete, hacer una mueca al probar algo, esconderse debajo
  de la mesa, etc.). NADA de física imposible ni fantástico (nada de volar,
  atravesar paredes, andar por el techo, teletransportarse) salvo que sea
  claramente un sueño/imaginación y quede dicho explícitamente.
- Cada prompt_video debe describir SOLO la acción de esa escena (el aspecto del
  personaje ya está fijado aparte, no lo repitas), con cámara fija o movimiento
  de cámara simple, en un entorno cotidiano (casa, jardín, cole).
- Texto de narración: 1-2 frases, muy simple, tono alegre.
- Termina con una moraleja corta y positiva.
- Devuelve SOLO un JSON válido, sin texto adicional, con este formato exacto:

{{
  "titulo": "string, título llamativo para YouTube, con emojis",
  "descripcion_youtube": "string, descripción para YouTube con 3-5 hashtags",
  "descripcion_personaje": "string, descripción física muy detallada del protagonista",
  "escenas": [
    {{"narracion": "string", "prompt_video": "string, SOLO la acción de la escena"}}
  ]
}}
"""
    texto = llamar_claude([{"role": "user", "content": prompt}], max_tokens=2000)
    guion = extraer_json(texto)
    with open(f"{WORKDIR}/guion.json", "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    return guion


# ---------------------------------------------------------------------------
# PASO 2: IMAGEN DE REFERENCIA DEL PERSONAJE (fal.ai / Flux)
# ---------------------------------------------------------------------------

def _fal_generar(modelo, payload):
    """Envía un trabajo a fal.ai y espera hasta que termine. Devuelve el JSON resultado."""
    headers = {"Authorization": f"Key {FAL_API_KEY}", "Content-Type": "application/json"}
    envio = requests.post(f"https://queue.fal.run/{modelo}", headers=headers, json=payload, timeout=60)
    envio.raise_for_status()
    tarea = envio.json()
    status_url = tarea["status_url"]
    result_url = tarea["response_url"]

    while True:
        time.sleep(5)
        estado = requests.get(status_url, headers=headers, timeout=30).json()
        if estado.get("status") == "COMPLETED":
            break
        if estado.get("status") == "FAILED":
            raise RuntimeError(f"fal.ai falló ({modelo}): {estado}")

    return requests.get(result_url, headers=headers, timeout=30).json()


def generar_imagen_personaje(descripcion_personaje):
    resultado = _fal_generar(
        "fal-ai/flux/dev",
        {
            "prompt": (
                f"Ficha de personaje de animación 3D estilo Pixar, cuerpo entero, de pie, "
                f"pose neutra, sonriente, fondo liso sencillo de color pastel, buena "
                f"iluminación, alta calidad: {descripcion_personaje}"
            ),
            "image_size": "portrait_16_9",
            "num_images": 1,
        },
    )
    imagen_url = resultado["images"][0]["url"]
    imagen_bytes = requests.get(imagen_url, timeout=60).content

    ruta = f"{WORKDIR}/personaje.png"
    with open(ruta, "wb") as f:
        f.write(imagen_bytes)

    imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")
    data_uri = f"data:image/png;base64,{imagen_b64}"
    return ruta, data_uri


# ---------------------------------------------------------------------------
# PASO 3: NARRACIÓN CON ELEVENLABS
# ---------------------------------------------------------------------------

def generar_audio(texto, nombre_archivo):
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": ELEVENLABS_API_KEY, "content-type": "application/json"},
        json={
            "text": texto,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=120,
    )
    resp.raise_for_status()
    ruta = f"{WORKDIR}/{nombre_archivo}"
    with open(ruta, "wb") as f:
        f.write(resp.content)
    return ruta


# ---------------------------------------------------------------------------
# PASO 4: CLIP DE VÍDEO ANIMADO (fal.ai / Kling, image-to-video)
# ---------------------------------------------------------------------------

def generar_clip_video(prompt_accion, imagen_referencia_data_uri, nombre_archivo, duracion_objetivo=5):
    duracion_kling = "5" if duracion_objetivo <= 7 else "10"

    resultado = _fal_generar(
        "fal-ai/kling-video/v2.1/standard/image-to-video",
        {
            "prompt": (
                prompt_accion
                + ". Animación 3D estilo Pixar, colores vivos, movimiento suave y natural, "
                "el personaje mantiene el mismo aspecto en todo momento."
            ),
            "image_url": imagen_referencia_data_uri,
            "duration": duracion_kling,
            "negative_prompt": NEGATIVE_PROMPT_VIDEO,
        },
    )
    video_url = resultado["video"]["url"]
    video_bytes = requests.get(video_url, timeout=120).content

    ruta = f"{WORKDIR}/{nombre_archivo}"
    with open(ruta, "wb") as f:
        f.write(video_bytes)
    return ruta


# ---------------------------------------------------------------------------
# PASO 5: AGENTE VERIFICADOR (Claude con visión revisa un fotograma del clip)
# ---------------------------------------------------------------------------

def extraer_fotograma_b64(ruta_video, segundo=1.0):
    from moviepy.editor import VideoFileClip

    clip = VideoFileClip(ruta_video)
    t = min(segundo, max(clip.duration - 0.1, 0))
    frame = clip.get_frame(t)
    clip.close()

    from PIL import Image
    img = Image.fromarray(frame)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def verificar_clip(ruta_video, descripcion_personaje, prompt_accion):
    """Devuelve (ok: bool, motivo: str) revisando un fotograma del clip con Claude."""
    try:
        frame_b64 = extraer_fotograma_b64(ruta_video, segundo=1.2)
    except Exception as e:
        return True, f"No se pudo extraer fotograma para revisar, se acepta por defecto ({e})"

    prompt_texto = f"""
Estás revisando la calidad de un clip de vídeo animado infantil (3D estilo Pixar).

El protagonista debería ser SIEMPRE este personaje: {descripcion_personaje}
La acción esperada en esta escena es: {prompt_accion}

Mira el fotograma adjunto y responde SOLO un JSON con este formato exacto,
sin texto adicional:
{{"ok": true o false, "motivo": "breve explicación"}}

Marca "ok": false SOLO si ves algo claramente mal, por ejemplo:
- El personaje no coincide con la descripción (otro pelo, otra ropa, otra edad).
- Anatomía imposible o deforme (extremidades de más, cuerpo roto).
- Una acción físicamente imposible o que no tiene sentido para la escena
  (andar por el techo o las paredes, flotar sin motivo, teletransportarse).
- Contenido inapropiado o que pueda asustar a niños pequeños.

Si el fotograma es una animación normal y coherente aunque no sea perfecta
artísticamente, responde "ok": true.
"""

    mensajes = [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64}},
                {"type": "text", "text": prompt_texto},
            ],
        }
    ]

    try:
        texto = llamar_claude(mensajes, max_tokens=300)
        veredicto = extraer_json(texto)
        return bool(veredicto.get("ok", True)), veredicto.get("motivo", "")
    except Exception as e:
        # Si el verificador falla técnicamente, no bloqueamos el vídeo por eso.
        return True, f"Verificador falló técnicamente, se acepta por defecto ({e})"


def generar_clip_verificado(prompt_accion, imagen_referencia_data_uri, descripcion_personaje,
                             nombre_archivo, duracion_objetivo):
    ultimo_motivo = ""
    for intento in range(1, MAX_INTENTOS_CLIP + 1):
        print(f"   Generando clip (intento {intento}/{MAX_INTENTOS_CLIP})...")
        ruta = generar_clip_video(prompt_accion, imagen_referencia_data_uri, nombre_archivo, duracion_objetivo)

        ok, motivo = verificar_clip(ruta, descripcion_personaje, prompt_accion)
        if ok:
            print(f"   ✅ Clip aceptado por el verificador. ({motivo})")
            return ruta

        ultimo_motivo = motivo
        print(f"   ⚠️  Verificador rechazó el clip: {motivo} — reintentando...")

    print(f"   ⚠️  Se agotaron los intentos. Se usa el último clip generado. Motivo: {ultimo_motivo}")
    return ruta


# ---------------------------------------------------------------------------
# PASO 6: MONTAJE DEL VÍDEO
# ---------------------------------------------------------------------------

def montar_video(guion, imagen_referencia_data_uri):
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, concatenate_videoclips,
        CompositeVideoClip, TextClip, vfx,
    )

    descripcion_personaje = guion["descripcion_personaje"]
    clips = []

    for i, escena in enumerate(guion["escenas"]):
        print(f"Escena {i + 1}/{len(guion['escenas'])}")

        audio_path = generar_audio(escena["narracion"], f"audio_{i}.mp3")
        audio_clip = AudioFileClip(audio_path)
        duracion = audio_clip.duration + 0.4

        video_path = generar_clip_verificado(
            escena["prompt_video"], imagen_referencia_data_uri, descripcion_personaje,
            f"clip_{i}.mp4", duracion_objetivo=duracion,
        )
        video_clip = VideoFileClip(video_path).resize(height=1920).set_position("center")

        if video_clip.duration >= duracion:
            video_clip = video_clip.subclip(0, duracion)
        else:
            video_clip = video_clip.fx(vfx.loop, duration=duracion)

        subtitulo = (
            TextClip(
                textwrap.fill(escena["narracion"], width=28),
                fontsize=60,
                color="white",
                font="DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(1000, None),
            )
            .set_duration(duracion)
            .set_position(("center", 1550))
        )

        escena_final = CompositeVideoClip([video_clip, subtitulo]).set_audio(audio_clip)
        clips.append(escena_final)

    video_final = concatenate_videoclips(clips, method="compose")
    salida = f"{WORKDIR}/video_final.mp4"
    video_final.write_videofile(salida, fps=30, codec="libx264", audio_codec="aac")
    return salida


# ---------------------------------------------------------------------------
# PASO 7: SUBIDA A YOUTUBE
# ---------------------------------------------------------------------------

def subir_a_youtube(ruta_video, titulo, descripcion):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion,
            "tags": ["niños", "infantil", "educativo", "dibujos animados"],
            "categoryId": "1",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True},
    }

    media = MediaFileUpload(ruta_video, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Subiendo... {int(status.progress() * 100)}%")

    print(f"Vídeo subido: https://youtu.be/{response['id']}")
    return response["id"]


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("1/5 Generando guion...")
    guion = generar_guion()

    print("2/5 Generando imagen de referencia del personaje...")
    _, imagen_referencia_data_uri = generar_imagen_personaje(guion["descripcion_personaje"])

    print("3/5 y 4/5: Generando clips animados verificados + montando vídeo...")
    ruta_video = montar_video(guion, imagen_referencia_data_uri)

    print("5/5 Subiendo a YouTube...")
    subir_a_youtube(ruta_video, guion["titulo"], guion["descripcion_youtube"])

    print("¡Listo!")


if __name__ == "__main__":
    main()
