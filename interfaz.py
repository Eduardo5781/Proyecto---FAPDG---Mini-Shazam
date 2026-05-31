import customtkinter as ctk
from PIL import Image
import threading
import os
import sys
import subprocess
import platform      # Detecta si es Windows o Mac
import unicodedata   # Elimina los acentos ocultos de los archivos

# Importamos tu lógica de reconocimiento (Intacta)
import reconocimiento

# Intentamos cargar Pygame para controlar el audio de forma multiplataforma
USAR_PYGAME = False
try:
    from pygame import mixer
    mixer.init()
    USAR_PYGAME = True
except ImportError:
    pass

# Ubicación de tu proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppReconocimiento(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.cancion_actual = None
        self.proceso_audio_mac = None

        # --- TRUCO ANTI-BUG PYTHON 3.13 ---
        self.img_invisible = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        self.foto_vacia_grande = ctk.CTkImage(light_image=self.img_invisible, dark_image=self.img_invisible, size=(600, 600))

        self.foto_grande = None

        # --- VENTANA PRINCIPAL (Tu Laptop) ---
        self.title("Panel de Control - Escáner Acústico")
        self.geometry("400x420+100+100")

        self.lbl_titulo = ctk.CTkLabel(self, text="Escáner Acústico", font=("Arial", 28, "bold"))
        self.lbl_titulo.pack(pady=20)

        self.lbl_estado = ctk.CTkLabel(self, text="Esperando instrucciones...", font=("Arial", 16))
        self.lbl_estado.pack(pady=10)

        self.btn_grabar = ctk.CTkButton(self, text="🎤 Iniciar Reconocimiento", 
                                        font=("Arial", 18), width=250, height=60,
                                        command=self.iniciar_proceso)
        self.btn_grabar.pack(pady=20)

        # --- CONTENEDOR PARA LOS BOTONES DE AUDIO ---
        self.frame_controles = ctk.CTkFrame(self, fg_color="transparent")

        self.btn_reproducir = ctk.CTkButton(self.frame_controles, text="▶️ Reproducir", 
                                            font=("Arial", 15, "bold"), fg_color="#2ecc71", hover_color="#27ae60",
                                            width=130, height=40, command=self.reproducir_cancion)
        self.btn_reproducir.pack(side="left", padx=10)

        self.btn_detener = ctk.CTkButton(self.frame_controles, text="⏹️ Detener", 
                                         font=("Arial", 15, "bold"), fg_color="#e74c3c", hover_color="#c0392b",
                                         width=130, height=40, command=self.detener_cancion)
        self.btn_detener.pack(side="left", padx=10)

        # --- VENTANA SECUNDARIA (La de 7" Externa) ---
        self.ventana_portada = ctk.CTkToplevel(self)
        self.ventana_portada.title("Pantalla de Visualización")
        self.ventana_portada.geometry("1024x600+1920+0") 
        self.ventana_portada.attributes('-fullscreen', True)

        self.lbl_imagen = ctk.CTkLabel(self.ventana_portada, image=self.foto_vacia_grande, text="🎶 Esperando música...", font=("Arial", 30))
        self.lbl_imagen.pack(expand=True, fill="both")

    # =========================================================
    # FUNCIÓN DE BÚSQUEDA INTELIGENTE (Anti-Acentos y Multiplataforma)
    # =========================================================
    def buscar_archivo_inteligente(self, carpeta, nombre_buscado, extensiones_validas):
        ruta_carpeta = os.path.join(BASE_DIR, carpeta)
        if not os.path.exists(ruta_carpeta):
            return None
            
        # Esta función elimina acentos, mayúsculas y signos raros
        def desinfectar(texto):
            texto_norm = unicodedata.normalize('NFKD', texto)
            return "".join(c.lower() for c in texto_norm if c.isalnum())
            
        target = desinfectar(nombre_buscado)
        
        for archivo in os.listdir(ruta_carpeta):
            nombre_real, ext = os.path.splitext(archivo)
            if ext.lower() in extensiones_validas:
                if desinfectar(nombre_real) == target:
                    return os.path.join(ruta_carpeta, archivo)
        return None

    # =========================================================
    # LÓGICA DE CONTROL
    # =========================================================
    def iniciar_proceso(self):
        self.btn_grabar.configure(state="disabled")
        self.frame_controles.pack_forget()
        self.detener_cancion()

        self.lbl_estado.configure(text="🔴 Grabando y Analizando (7s)...", text_color="orange")
        self.lbl_imagen.configure(image=self.foto_vacia_grande, text="Procesando audio...", text_color="white")

        hilo = threading.Thread(target=self.ejecutar_reconocimiento)
        hilo.start()

    def ejecutar_reconocimiento(self):
        resultado = reconocimiento.reconocer_cancion()
        self.after(0, self.actualizar_ui, resultado)

    def actualizar_ui(self, resultado):
        self.btn_grabar.configure(state="normal")

        if resultado is not None:
            cancion, score = resultado
            self.cancion_actual = cancion
            
            self.lbl_estado.configure(text=f"✅ ¡Encontrada!\n\n🎵 {cancion}\nMatch Score: {score}", text_color="green")
            self.mostrar_portada(cancion)
            self.frame_controles.pack(pady=15)
        else:
            self.cancion_actual = None
            self.lbl_estado.configure(text="❌ No se encontró coincidencia.", text_color="red")
            self.lbl_imagen.configure(image=self.foto_vacia_grande, text="❌ Intenta de nuevo", text_color="red")

    def reproducir_cancion(self):
        if not self.cancion_actual:
            return

        ruta_audio = self.buscar_archivo_inteligente("dataset_canciones", self.cancion_actual, ['.mp3', '.wav', '.m4a'])

        if ruta_audio:
            # 1. INTENTO CON PYGAME (Para todos los OS)
            if USAR_PYGAME:
                try:
                    mixer.music.load(ruta_audio)
                    mixer.music.play()
                    self.lbl_estado.configure(text=f"▶️ Reproduciendo:\n{self.cancion_actual}", text_color="cyan")
                    return
                except:
                    pass

            # 2. FALLBACK NATIVO (Si no tienen Pygame instalado)
            sistema = platform.system()
            try:
                if sistema == "Darwin": # Mac
                    if self.proceso_audio_mac and self.proceso_audio_mac.poll() is None:
                        self.proceso_audio_mac.terminate()
                    self.proceso_audio_mac = subprocess.Popen(["afplay", ruta_audio])
                    self.lbl_estado.configure(text=f"▶️ Reproduciendo:\n{self.cancion_actual}", text_color="cyan")
                
                elif sistema == "Windows": # Windows
                    os.startfile(ruta_audio)
                    self.lbl_estado.configure(
                        text=f"▶️ Reproduciendo (Windows)\nℹ️ Tip: Corre 'pip install pygame' para poder usar el botón detener.", 
                        text_color="yellow"
                    )
            except Exception as e:
                self.lbl_estado.configure(text=f"❌ Error al reproducir audio:\n{e}", text_color="red")
        else:
            self.lbl_estado.configure(
                text=f"⚠️ No se encontró el archivo para:\n'{self.cancion_actual}' en dataset_canciones/", 
                text_color="yellow"
            )

    def detener_cancion(self):
        # Detener en Pygame
        if USAR_PYGAME:
            mixer.music.stop()
        
        # Detener en Mac nativo
        if self.proceso_audio_mac and self.proceso_audio_mac.poll() is None:
            self.proceso_audio_mac.terminate()
            self.proceso_audio_mac = None
            
        self.lbl_estado.configure(text=f"⏹️ Audio detenido.\n\n🎵 {self.cancion_actual}", text_color="white")

    def mostrar_portada(self, nombre_cancion):
        ruta_imagen = self.buscar_archivo_inteligente("portadas", nombre_cancion, ['.png', '.jpg', '.jpeg'])
        
        if ruta_imagen:
            try:
                imagen_cruda = Image.open(ruta_imagen)
                self.foto_grande = ctk.CTkImage(light_image=imagen_cruda, dark_image=imagen_cruda, size=(600, 600))
                self.lbl_imagen.configure(image=self.foto_grande, text="")
            except Exception as e:
                msg_error = f"Error cargando imagen:\n{e}"
                self.lbl_imagen.configure(image=self.foto_vacia_grande, text=msg_error, text_color="red")
        else:
            msg_vacio = f"Imagen no encontrada para:\n{nombre_cancion}"
            self.lbl_imagen.configure(image=self.foto_vacia_grande, text=msg_vacio, text_color="yellow")

if __name__ == "__main__":
    app = AppReconocimiento()
    app.mainloop()