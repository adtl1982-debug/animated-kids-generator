# 🎬 Agente automático de vídeos infantiles para YouTube

Genera cada día, sin que tengas que tocar nada, un vídeo corto de comedia
educativa para niños de 2 a 5 años, en español, y lo sube solo a tu canal
de YouTube.

Esta guía está escrita para alguien que **no sabe programar**. Sigue los
pasos en orden, tal cual.

---

## Qué hace por dentro (no necesitas entenderlo, solo saberlo)

1. Claude (Anthropic) escribe el guion: describe con detalle un ÚNICO personaje
   protagonista y luego escribe 4-6 escenas de comedia con moraleja, siempre
   con ese mismo personaje.
2. fal.ai (Flux) genera UNA imagen de referencia de ese personaje — es la que
   se usará como "punto de partida" en todas las escenas, para que sea siempre
   el mismo niño (mismo pelo, ropa, cara).
3. ElevenLabs convierte cada narración en audio.
4. fal.ai (Kling) anima cada escena a partir de esa imagen de referencia +
   la acción de la escena — así el personaje no cambia de una escena a otra.
5. Un AGENTE VERIFICADOR (Claude, con visión) revisa un fotograma de cada
   clip generado: comprueba que el personaje coincide con la descripción y que
   no hay nada físicamente imposible o raro (andar por el techo, extremidades
   de más, etc.). Si algo falla, pide regenerar ese clip automáticamente
   (hasta 2 veces más) antes de continuar.
6. El programa monta el vídeo final (clips + voz + subtítulos).
7. YouTube recibe el vídeo y lo publica en tu canal automáticamente.
8. GitHub Actions repite este proceso todos los días a la hora que tú digas,
   sin que tu ordenador tenga que estar encendido.

**Nota sobre coste y tiempo**: esta versión con vídeo animado + verificación
es más lenta (puede tardar 20-40 minutos en total) y más cara por vídeo que la
versión con imágenes estáticas, porque genera más contenido con IA (imagen de
personaje + clips de vídeo + posibles reintentos + revisiones con Claude). Con
tu presupuesto debería ir sobrado, pero si quieres reducir el gasto, dímelo y
ajustamos el número de escenas o los reintentos máximos.

---

## PASO 1 — Crear el repositorio en GitHub

1. Entra en tu perfil: https://github.com/adtl1982-debug
2. Arriba a la derecha pulsa el botón **"+"** → **"New repository"**.
3. Nombre del repositorio: `kids-video-agent` (o el que prefieras).
4. Marca **Private** (privado), para que nadie vea tus claves ni tu código.
5. Pulsa **Create repository**.

## PASO 2 — Subir estos archivos a tu repositorio

Te he generado ya todos los archivos (los verás abajo, en "Archivos"). Dos
formas de subirlos, elige la que te resulte más fácil:

**Opción fácil (sin terminal):**
1. Descarga todos los archivos que te he compartido.
2. En la página de tu repositorio vacío, pulsa **"uploading an existing file"**.
3. Arrastra todos los archivos y carpetas (incluida la carpeta `.github`).
4. Pulsa **Commit changes**.

**Opción con terminal (si tienes Git instalado):**
```bash
git clone https://github.com/adtl1982-debug/kids-video-agent.git
cd kids-video-agent
# copia aquí dentro todos los archivos que te he generado
git add .
git commit -m "Primer commit del agente"
git push
```

## PASO 3 — Conseguir las claves de API (esto es lo único "pesado", pero es solo una vez)

### 3.1 Clave de Anthropic (Claude) — escribe los guiones
1. Ve a https://console.anthropic.com → **Get API Keys** → **Create Key**.
2. Copia la clave (empieza por `sk-ant-...`). Necesitarás crédito en la cuenta
   (con unos pocos euros al mes sobra para un vídeo diario).

### 3.2 Clave de ElevenLabs — voz narrada
1. Crea cuenta en https://elevenlabs.io
2. Ve a tu perfil (icono arriba a la derecha) → **API Keys** → copia la clave.
3. Opcional: en **VoiceLab** elige o clona una voz infantil/cálida y copia su
   "Voice ID" (si no, el agente usa una voz por defecto).
4. Con tu presupuesto (+30€/mes), el plan "Creator" te da voces de alta calidad
   e ilimitadas para esto.

### 3.3 Clave de fal.ai — clips de vídeo animado (Kling)
1. Crea cuenta en https://fal.ai
2. Al registrarte te dan 10$ de crédito gratis (sirve para tus primeras pruebas).
3. Ve a **Dashboard** → **Keys** → **Create key** → copia la clave.
4. Cuando se agote el crédito gratis, añade saldo desde **Billing** (el coste por
   vídeo suele ser de pocos céntimos a poco más de 1€, según duración).

### 3.4 Credenciales de YouTube (esto sube el vídeo a tu canal)
1. Ve a https://console.cloud.google.com → crea un proyecto nuevo (nombre libre,
   ej. "kids-video-agent").
2. Menú ☰ → **APIs & Services** → **Library** → busca **"YouTube Data API v3"**
   → **Enable**.
3. **APIs & Services** → **OAuth consent screen** → tipo **External** →
   rellena nombre de la app y tu email → guarda (no hace falta publicarla,
   basta con dejarla en modo "Testing" y añadirte a ti mismo como
   "Test user").
4. **APIs & Services** → **Credentials** → **Create Credentials** →
   **OAuth client ID** → tipo de aplicación: **Desktop app** → Create.
5. Descarga el archivo JSON generado, renómbralo a `client_secret.json`.
6. En tu ordenador (no en GitHub), en la misma carpeta del proyecto:
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python get_youtube_refresh_token.py
   ```
7. Se abrirá el navegador: inicia sesión con la cuenta de Google dueña del
   canal de YouTube y acepta los permisos.
8. En la terminal aparecerán 3 valores: `YOUTUBE_CLIENT_ID`,
   `YOUTUBE_CLIENT_SECRET` y `YOUTUBE_REFRESH_TOKEN`. Guárdalos, los usarás
   en el paso siguiente.

## PASO 4 — Guardar las claves como "Secrets" en GitHub

1. En tu repositorio → **Settings** → **Secrets and variables** → **Actions**.
2. Pulsa **New repository secret** y crea uno por cada clave (nombre exacto
   a la izquierda, valor a la derecha):

| Nombre del secret        | Valor                                  |
|---------------------------|-----------------------------------------|
| `ANTHROPIC_API_KEY`       | tu clave de Anthropic                   |
| `ELEVENLABS_API_KEY`      | tu clave de ElevenLabs                  |
| `ELEVENLABS_VOICE_ID`     | (opcional) el Voice ID que elegiste     |
| `FAL_API_KEY`             | tu clave de fal.ai                      |
| `YOUTUBE_CLIENT_ID`       | del paso 3.4                            |
| `YOUTUBE_CLIENT_SECRET`   | del paso 3.4                            |
| `YOUTUBE_REFRESH_TOKEN`   | del paso 3.4                            |

## PASO 5 — Probarlo

1. En tu repositorio, pestaña **Actions**.
2. Si aparece un aviso pidiendo activar Actions, acéptalo.
3. Selecciona el workflow **"Generar y subir vídeo infantil"** → botón
   **Run workflow** → **Run workflow** (verde).
4. Espera unos minutos y verás si termina en verde (✅, éxito) o rojo
   (❌, error — pulsa encima para ver el mensaje de error exacto).
5. Si todo va bien, el vídeo aparecerá publicado en tu canal de YouTube.

A partir de aquí, el agente se ejecutará **solo, cada día a las 09:00 UTC**
(puedes cambiar la hora editando la línea `cron` en el archivo
`.github/workflows/generate_and_upload.yml`).

---

## Cómo cambiar el tema de los vídeos

Por defecto, cada día Claude elige una situación cotidiana distinta. Si
quieres forzar un tema concreto un día, añade un secret opcional llamado
`TEMA_DEL_DIA` con el texto del tema (ej. "aprender a compartir juguetes").

## Errores típicos y solución rápida

- **Error de crédito insuficiente**: revisa el saldo en Anthropic /
  ElevenLabs / Stability AI.
- **Error 403 de YouTube**: la cuenta de Google usada en el paso 3.4 no es
  la dueña del canal, o el proyecto de Google Cloud sigue en modo
  "Testing" sin haberte añadido como "Test user".
- **El vídeo no tiene subtítulos / falla ImageMagick**: ya está resuelto en
  el workflow (paso que ajusta la política de seguridad), pero si sigue
  fallando, dímelo y lo revisamos juntos.

## Siguientes mejoras posibles (cuando quieras)

- Generar miniaturas (thumbnails) automáticas con IA.
- Publicar también como Shorts en TikTok/Instagram con el mismo vídeo.
- Añadir música de fondo libre de derechos.
- Panel de control para revisar el guion antes de publicar (aprobación
  manual antes de subir).

Cuando quieras, seguimos con cualquiera de estas mejoras paso a paso.
