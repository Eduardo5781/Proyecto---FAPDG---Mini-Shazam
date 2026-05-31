import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

# Frecuencia de muestreo definida para el proyecto
FS = 44100 

def disenar_fir(f_low=80, f_high=5000, numtaps=101):
    """
    Diseña un filtro FIR pasa-banda usando ventana Hann.
    """
    nyq = 0.5 * FS
    # Normalizamos las frecuencias respecto a la frecuencia de Nyquist
    low = f_low / nyq
    high = f_high / nyq
    
    # firwin por defecto utiliza la ventana 'hann'
    taps = signal.firwin(numtaps, [low, high], pass_zero=False, window='hann')
    return taps

def aplicar_fir(data, taps):
    """
    Aplica el filtro FIR a la señal de audio (usado en la Fase de Registro).
    """
    # Para un filtro FIR, los coeficientes del denominador 'a' son 1.0
    senal_filtrada = signal.lfilter(taps, 1.0, data)
    return senal_filtrada

def disenar_iir(f_cutoff=5000, order=4):
    """
    Diseña un filtro IIR Butterworth pasa-bajas.
    """
    nyq = 0.5 * FS
    normal_cutoff = f_cutoff / nyq
    
    # b = coeficientes del numerador, a = coeficientes del denominador
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def aplicar_iir(data, b, a):
    """
    Aplica el filtro IIR a la señal de audio (usado en tiempo real en la Fase de Reconocimiento).
    """
    senal_filtrada = signal.lfilter(b, a, data)
    return senal_filtrada

def graficar_respuesta_frecuencia(b, a=1.0, titulo="Respuesta en Frecuencia del Filtro"):
    """
    Calcula y grafica la respuesta en magnitud del filtro.
    """
    # freqz calcula la respuesta en frecuencia del filtro digital
    w, h = signal.freqz(b, a, worN=8000)
    
    # Convertimos la frecuencia normalizada a Hz
    frecuencias = (w * FS) / (2 * np.pi)
    
    plt.figure(figsize=(10, 5))
    plt.plot(frecuencias, 20 * np.log10(np.abs(h)), 'b')
    plt.title(titulo)
    plt.ylabel('Amplitud [dB]')
    plt.xlabel('Frecuencia [Hz]')
    plt.grid(which='both', axis='both')
    
    # Acotamos el eje X a 10 kHz para visualizar mejor la banda de interés
    plt.xlim(0, 10000) 
    plt.ylim(-100, 5)
    plt.tight_layout()
    plt.show()

# ==========================================
# BLOQUE DE PRUEBA (Opcional, para verificar)
# ==========================================
if __name__ == "__main__":
    # Prueba del Filtro FIR pasa-banda (80 - 5000 Hz)
    taps_fir = disenar_fir()
    graficar_respuesta_frecuencia(taps_fir, 1.0, "Respuesta en Frecuencia - FIR Pasa-banda (Registro)")
    
    # Prueba del Filtro IIR Butterworth pasa-bajas (Corte en 5000 Hz)
    b_iir, a_iir = disenar_iir()
    graficar_respuesta_frecuencia(b_iir, a_iir, "Respuesta en Frecuencia - IIR Pasa-bajas (Reconocimiento)")