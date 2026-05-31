import os
import sqlite3
import librosa
import filtros
import fingerprint

# ==============================================================================
# CONFIGURACIÓN DE RUTAS
# ==============================================================================
# El documento pide guardar la base de datos en una carpeta llamada 'database' 
DB_PATH = "database/canciones.db"
# El documento especifica 20 canciones descargadas de Kaggle [cite: 13, 21, 38]
DIRECTORIO_CANCIONES = "dataset_canciones"

# ==============================================================================
# FUNCIÓN 1: CREAR BASE DE DATOS
# ==============================================================================
def crear_base_datos():
    """
    Crea el archivo canciones.db y las dos tablas necesarias (canciones y hashes)[cite: 60].
    """
    # Aseguramos que la carpeta database/ exista
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # Tabla 'canciones' con id, nombre y archivo [cite: 61, 62, 63, 64]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            archivo TEXT NOT NULL
        )
    ''')

    # Tabla 'hashes' con hash_hex, cancion_id y tiempo [cite: 65, 66, 67, 68]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hashes (
            hash_hex TEXT NOT NULL,
            cancion_id INTEGER NOT NULL,
            tiempo REAL NOT NULL,
            FOREIGN KEY (cancion_id) REFERENCES canciones (id)
        )
    ''')

    # Índice para acelerar las búsquedas (crucial para la complejidad O(n)) [cite: 70]
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON hashes(hash_hex)')

    conexion.commit()
    conexion.close()
    print("Base de datos estructurada correctamente en 'database/canciones.db'.")

# ==============================================================================
# FUNCIÓN 2: PROCESAR Y REGISTRAR LAS CANCIONES
# ==============================================================================
def registrar_canciones_offline():
    """
    Carga las canciones , aplica el filtro FIR[cite: 23, 38], 
    extrae el fingerprint  y guarda los hashes en SQLite.
    """
    if not os.path.exists(DIRECTORIO_CANCIONES):
        print(f"Error: Crea la carpeta '{DIRECTORIO_CANCIONES}' y mete ahí las 20 canciones.")
        return

    # Diseñamos el filtro FIR pasa-banda (80 Hz - 5,000 Hz, ventana Hann) [cite: 23]
    print("Generando filtro FIR pasa-banda...")
    taps_fir = filtros.disenar_fir()
    
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    archivos_audio = [f for f in os.listdir(DIRECTORIO_CANCIONES) if f.endswith(('.wav', '.mp3'))]
    
    if not archivos_audio:
        print("No hay canciones en la carpeta para registrar.")
        return

    print(f"Se encontraron {len(archivos_audio)} archivos. Iniciando Fase de Registro...")

    for archivo in archivos_audio:
        ruta_completa = os.path.join(DIRECTORIO_CANCIONES, archivo)
        nombre_cancion = os.path.splitext(archivo)[0]
        
        # Verificar si la canción ya está en la BD para evitar duplicados
        cursor.execute("SELECT id FROM canciones WHERE archivo = ?", (ruta_completa,))
        if cursor.fetchone():
            print(f" -> Omitiendo '{nombre_cancion}', ya está registrada.")
            continue
            
        print(f"Procesando: {nombre_cancion}...")
        
        try:
            # 1. Muestreo y cuantización a fs = 44,100 Hz [cite: 22]
            y, sr = librosa.load(ruta_completa, sr=44100, mono=True)
            
            # 2. Aplicar el filtro FIR pasa-banda importado de filtros.py 
            y_filtrado = filtros.aplicar_fir(y, taps_fir)
            
            # 3. Obtener la huella espectral (hashes) usando fingerprint.py 
            hashes, _ = fingerprint.obtener_fingerprint(y_filtrado, fs=sr)
            
            # 4. Guardar en la tabla 'canciones'
            cursor.execute("INSERT INTO canciones (nombre, archivo) VALUES (?, ?)", (nombre_cancion, ruta_completa))
            cancion_id = cursor.lastrowid
            
            # 5. Guardar los hashes generados en la tabla 'hashes' masivamente
            datos_hashes = [(h[0], cancion_id, h[1]) for h in hashes]
            cursor.executemany("INSERT INTO hashes (hash_hex, cancion_id, tiempo) VALUES (?, ?, ?)", datos_hashes)
            
            conexion.commit()
            print(f"    ¡Éxito! Se guardaron {len(hashes)} hashes.")
            
        except Exception as e:
            print(f"    Error al procesar '{nombre_cancion}': {e}")

    conexion.close()
    print("\n¡Fase de Registro (Offline) completada! La base de datos está lista[cite: 20].")

# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    crear_base_datos()
    registrar_canciones_offline()