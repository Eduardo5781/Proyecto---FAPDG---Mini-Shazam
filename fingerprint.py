import numpy as np
import librosa
import scipy.ndimage
import hashlib
import sqlite3
import matplotlib.pyplot as plt

def calcular_fft(x):
    """
    Implementación explícita del algoritmo FFT Cooley-Tukey.
    Requiere que la longitud de la señal de entrada sea potencia de 2.
    """
    x = np.asarray(x, dtype=float)
    N = x.shape[0]
    
    if N <= 1:
        return x
    elif N % 2 != 0:
        # Manejo de seguridad por si la ventana no es potencia de 2
        return np.fft.fft(x)
        
    # División de la señal en partes par e impar
    par = calcular_fft(x[0::2])
    impar = calcular_fft(x[1::2])
    
    # Factor de giro (twiddle factor)
    factor = np.exp(-2j * np.pi * np.arange(N // 2) / N)
    T = factor * impar
    
    # Combinación recursiva (Butterfly)
    return np.concatenate([par + T, par - T])

def calcular_espectrograma(audio, fs=44100):
    """
    Calcula el espectrograma tiempo-frecuencia usando STFT[cite: 24, 32].
    """
    # librosa.stft es altamentente eficiente para procesar las ventanas del espectro [cite: 73]
    stft_matrix = librosa.stft(audio, n_fft=2048, hop_length=512)
    espectrograma = np.abs(stft_matrix)
    return espectrograma

def detectar_picos(espectrograma):
    """
    Encuentra los picos de máxima energía (constellation map) trabajando en escala logarítmica (dB).
    """
    espectrograma_limpio = np.copy(espectrograma)
    espectrograma_limpio[:4, :] = 0  # Apagamos la banda baja
    
    # Convertimos a dB para tener una escala universal (0 a -80 dB típicamente)
    espectrograma_db = librosa.amplitude_to_db(espectrograma_limpio, ref=np.max)
    
    # Vecindario para el máximo local
    vecindario = np.ones((20, 20))
    filtro_local = scipy.ndimage.maximum_filter(espectrograma_db, footprint=vecindario) == espectrograma_db
    
    # Umbral relativo: top 5% de la energía
    umbral_relativo = np.percentile(espectrograma_db, 95)
    
    # Umbral absoluto: ignorar todo lo que esté por debajo de -45 dB (ruido de fondo)
    umbral_absoluto = -45.0 
    
    umbral_final = max(umbral_relativo, umbral_absoluto)
    
    picos_booleanos = filtro_local & (espectrograma_db > umbral_final)
    
    frecuencias, tiempos = np.where(picos_booleanos)
    return list(zip(frecuencias, tiempos))

def generar_hashes(picos):
    """
    Genera hashes SHA1 combinando (f1 | f2 | delta_t).
    """
    hashes = []
    picos.sort(key=lambda x: x[1])
    
    for i in range(len(picos)):
        for j in range(1, 15): 
            if i + j < len(picos):
                f1, t1 = picos[i]
                f2, t2 = picos[i + j]
                delta_t = t2 - t1
                
                if delta_t > 0:
                    # Convertimos todo explícitamente a int nativo de Python
                    hash_str = f"{int(f1)}|{int(f2)}|{int(delta_t)}"
                    hash_hex = hashlib.sha1(hash_str.encode('utf-8')).hexdigest()
                    
                    # Guardamos t1 ya convertido a int para que SQLite no se confunda
                    hashes.append((hash_hex, int(t1)))
    return hashes

def obtener_fingerprint(audio, fs=44100):
    """
    Función envolvente que extrae la huella completa del audio[cite: 33, 38].
    """
    espectrograma = calcular_espectrograma(audio, fs)
    picos = detectar_picos(espectrograma)
    hashes = generar_hashes(picos)
    return hashes, espectrograma

def buscar_cancion(hashes_fragmento, db_path="canciones.db"):
    """
    Busca coincidencias usando alineación temporal (Histograma de Offsets).
    Compara que los hashes ocurran con la misma diferencia de tiempo.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Diccionario para contar cuántas veces se repite un (cancion_id, offset)
        conteo_offsets = {}
        
        # Iteramos sobre los hashes del micrófono
        for hash_hex, tiempo_mic in hashes_fragmento:
            
            # --- ESTAS SON LAS LÍNEAS QUE FALTABAN ---
            # Buscamos en la BD los tiempos donde aparece este hash específico
            cursor.execute("SELECT cancion_id, tiempo FROM hashes WHERE hash_hex = ?", (hash_hex,))
            resultados = cursor.fetchall()
            # -----------------------------------------
            
           # ... (código previo) ...
            cursor.execute("SELECT cancion_id, tiempo FROM hashes WHERE hash_hex = ?", (hash_hex,))
            resultados = cursor.fetchall()
            
            for cancion_id, tiempo_bd in resultados:
                # Como ya guardamos enteros limpios, esto funcionará directo
                t_bd = int(tiempo_bd)
                t_mic = int(tiempo_mic)
                
                offset_bruto = t_bd - t_mic
                offset_agrupado = offset_bruto // 4
                
                clave = (cancion_id, offset_agrupado)
                conteo_offsets[clave] = conteo_offsets.get(clave, 0) + 1
            # ... (resto del código) ...
                
        conn.close()
        
        if not conteo_offsets:
            return None, 0
            
        # --- DIAGNÓSTICO DE ALINEACIÓN TEMPORAL ---
        top_resultados = sorted(conteo_offsets.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"\n--- TOP 3 ALINEACIONES TEMPORALES ---")
        for (cid, off), score in top_resultados:
            print(f" Canción ID: {cid} | Offset: {off} | Votos (Score): {score}")
        print("-------------------------------------\n")
            
        # Buscamos el par (cancion_id, offset) que acumuló más coincidencias
        mejor_coincidencia = top_resultados[0][0] 
        cancion_ganadora = mejor_coincidencia[0]
        max_coincidencias = conteo_offsets[mejor_coincidencia]
        
        return cancion_ganadora, max_coincidencias
        
    except sqlite3.Error as e:
        print(f"Error interno con la base de datos: {e}")
        return None, 0

def graficar_espectrograma(espectrograma):
    """
    Visualiza el espectrograma usando Matplotlib.
    """
    plt.figure(figsize=(10, 4))
    # Transformación a escala logarítmica (dB) para poder visualizar el espectro correctamente
    espectrograma_db = librosa.amplitude_to_db(espectrograma, ref=np.max)
    plt.imshow(espectrograma_db, aspect='auto', origin='lower', cmap='viridis')
    plt.title('Espectrograma STFT')
    plt.ylabel('Frecuencia (Bins)')
    plt.xlabel('Tiempo (Frames)')
    plt.colorbar(format='%+2.0f dB')
    plt.tight_layout()
    plt.show()