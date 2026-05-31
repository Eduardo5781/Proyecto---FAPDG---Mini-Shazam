import sounddevice as sd
import numpy as np
import sqlite3
import filtros
import fingerprint
import librosa

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
FS = 44100
DURACION = 7  # Grabaremos 7 segundos
DB_PATH = "database/canciones.db"

def grabar_audio(duracion=DURACION, fs_objetivo=FS):
    print(f"\n🎤 GRABANDO ({duracion} segundos)... ¡Acerca la música al micrófono!")
    
    fs_hardware = 48000 
    
    # Grabamos en Mono (channels=1) con tu AudioPro X5 (device=15)
    grabacion = sd.rec(int(duracion * fs_hardware), samplerate=fs_hardware, channels=1, dtype='float32', device=5)
    sd.wait()
    
    audio_aplanado = np.squeeze(grabacion)
    
    # --- DIAGNÓSTICO DE AMPLITUD ---
    amplitud_max = np.max(np.abs(audio_aplanado))
    print(f" -> Nivel de entrada del micrófono: {amplitud_max:.5f} (Ideal: > 0.1)")
    if amplitud_max < 0.05:
        print(" ⚠️ ALERTA: Micrófono casi sordo. Python no está escuchando la música.")
        
    print("🔄 Adaptando la frecuencia de muestreo del hardware...")
    audio_remuestreado = librosa.resample(y=audio_aplanado, orig_sr=fs_hardware, target_sr=fs_objetivo)
    
    return audio_remuestreado

def reconocer_cancion():
    # 1. Grabar audio del entorno 
    audio_mic = grabar_audio()

    # Compuerta de ruido y Normalización
    max_amp = np.max(np.abs(audio_mic))
    if max_amp > 0.05:
        audio_mic = audio_mic / max_amp
    else:
        print("⚠️ ADVERTENCIA: Nivel de audio muy bajo. ¿Está sonando la música?")

    # 2. Aplicar filtro FIR pasa-banda
    print("🧹 Limpiando ruido con filtro FIR pasa-banda...")
    taps_fir = filtros.disenar_fir()
    audio_filtrado = filtros.aplicar_fir(audio_mic, taps_fir)

    # 3. Extraer la huella espectral
    print("🔍 Analizando espectrograma y extrayendo hashes...")
    hashes_fragmento, espectrograma = fingerprint.obtener_fingerprint(audio_filtrado, fs=FS)

    if not hashes_fragmento:
        print("❌ No se encontraron suficientes picos de energía en el audio.")
        return None

    print(f"    -> Se generaron {len(hashes_fragmento)} hashes del micrófono.")

    # 4. Consultar SQLite
    print("📊 Buscando coincidencias en la base de datos...")
    cancion_id, coincidencias = fingerprint.buscar_cancion(hashes_fragmento, db_path=DB_PATH)

    if cancion_id is None or coincidencias == 0:
        print("❌ No se encontró ninguna canción coincidente.")
        return None

    # 5. Recuperar el nombre
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM canciones WHERE id = ?", (cancion_id,))
    resultado = cursor.fetchone()
    conexion.close()

    if resultado:
        print("\n==================================================")
        print(f"🎵 ¡CANCION IDENTIFICADA! 🎵")
        print(f"Título: {resultado[0]}")
        print(f"Score: {coincidencias}")
        print("==================================================\n")
        
        # Le mandamos los datos a la interfaz gráfica
        return resultado[0], coincidencias
    else:
        print("Error: Se encontró un ID, pero no existe en el catálogo.")
        return None