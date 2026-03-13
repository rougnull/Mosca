Arreglar el error de la simulacion -> sigue "metiendose" dentro del suelo ya que la z varía mucho, de 0.18 a 2.29 de la ultima simulacion: outputs\simulations\physics_3d\2026-03-12_21_45

Los joints y sus angulos no parecen estár bien, el analizador de simulaciones solo detecta un joint cuando deberia haber 6? (6 patas y sus demas articulaciones)

Las acciones motoras parecen estar bien pero se puede comprobar tambien.

Puede ser util ejecutar unicamente el test del cerebro y visualizar como este indica el "acercarse" al olor en una especie de grafica, y ver como cambia el estimulo motor segun se va acercando al gradiente del olor (el olor es mas atractivo)

Puede ser util analizar tambien mirar el codigo del analizador de simulacion y verificar si esta leyendo bien los datos de las extremidades. Para ver si es un error del analizador o de la propia simulacion o de la extraccion de datos en bruto .pk1

Otro posible fallo obiamente es (si el cerebro funciona como es esperado) es la "compatibilidad" o comunicacion entre el cerebro y el simulador de fisicas y sus extremidades, puede que el cerebro solo interprete un ir acercarse o alejarse, pero el simulador no sabe que es lo que realmete significa esto ni hacia donde acercase ni alejarse.

Verificar que el cpg funciona de verdad, hacer una simulacion sin cerebro, solo que cpg reciba señales de avanzar y que este mueva las extremidades de la mosca correctamente. otra cosa rara es que si el cerebro solo devuelve informacion del tipo avanzar hacia alante o hacia atras; cpg realmente no sabe que interpretar el cuando girar o cuando dejar de andar; seguramente haya que mejorar los outputs del cerebro, la compatibilidad con cpg y los diferentes movimientos que este puede hacer, como pararse (stalling si ya esta en el origen del olor o muy cerca) o que sepa como ir girando hacia el centro del olor.

A parte de los errores hay que modular el codigo y actualizar el "codigo principal" que son los archivos render_enhanced_3d_v2.py que son los archivos que deberian implementar todas las funcionalidades para "hacer la simulacion y render final". Cuando ya tengamos claro que todo está correcto.

En la linea 186 se guarda la informacion de la trayectoria como simples arrays? esto seguro que genera algun tipo de problema. Ademas, es correcto el uso de pickle para guardar los datos de la trayectoria? porque es esto util? 
# Storage for trajectory data
        self.trajectory_data = {
            "times": [],
            "positions": [],
            "headings": [],
            "orientations": [],
            "odor_concentrations": [],
            "brain_actions": [],
            "joint_angles": [],
            "contact_forces": [],
        }

Basado en la arquitectura y la documentación de tu proyecto "Mosca", tu diagnóstico es muy acertado. Aquí tienes un análisis de por qué está pasando cada cosa y cómo solucionarlo apoyándome en la estructura de tu código:

**1. El error de la simulación (la mosca se "hunde" en el suelo)**
Este es un problema mecánico detectado en la configuración de las patas dentro del simulador de físicas. Según los registros de actualización de tu proyecto, la mosca no logra mantener la altura (z varía) porque la postura base de las patas no ejerce suficiente fuerza contra el suelo. Para solucionarlo, debes aplicar los siguientes ajustes críticos en el controlador:
*   **Extensión del fémur (Femur Extension):** Ajustar el *offset* del fémur de -0.8 a -0.5 radianes para darle una postura más erguida [1].
*   **Soporte del CPG:** Aumentar la amplitud base de las patas en el controlador CPG de 0.5 a 0.7 [1]. 
Con estos cambios, la mosca debería mantener una altura estable en el eje Z (> 1.5mm) y no hundirse [2].

**2. El analizador solo detecta 1 joint en lugar de 42 (y extracción del `.pkl`)**
Una mosca en FlyGym tiene 6 patas con 7 grados de libertad (DoF) cada una, lo que suma **42 articulaciones** [2, 3]. Si el analizador solo detecta un joint (o un array de dimensiones incorrectas), el error está casi garantizado en la **extracción de datos en bruto del archivo `simulation_data.pkl`** [2, 4]. 
*   **Por qué pasa:** Tu sistema tiene diferentes niveles de abstracción. El `OlfactoryBrain` genera un comando de solo 2 dimensiones: `[forward, turn]` [5, 6]. Es muy probable que tu script de guardado esté registrando la salida del *cerebro* (la intención de movimiento) en lugar de la salida del *CPG Controller* (las acciones de las 42 articulaciones que realmente van a MuJoCo) [5]. Debes revisar que tu código de análisis extraiga el diccionario de acciones (`action dict`) del nivel físico y no solo la variable cognitiva [5].

**3. Visualización del cerebro ("acercarse" al olor)**
Tu idea de ejecutar una prueba aislada del cerebro es excelente y necesaria. Tu módulo `ImprovedOlfactoryBrain` fue actualizado recientemente para arreglar un problema donde la mosca se alejaba al estar muy cerca de la fuente [7]. 
*   Para la gráfica, debes visualizar el **gradiente temporal** ($dC/dt$) frente a la acción `forward` [2, 7]. El cerebro ahora está programado para que el motor "forward" se active *únicamente cuando la concentración aumenta* (previniendo que la mosca siga de largo o haga *overshooting*) [7, 8]. 
*   Para el giro (`turn`), debes graficar la diferencia de concentración entre la antena izquierda y la derecha (separadas biológicamente por 1.2 mm), ya que el cerebro usa esta comparación bilateral para la quimiotaxis [2, 6, 8].

**4. "Compatibilidad" o comunicación entre el cerebro y el simulador de físicas**
Este es el núcleo de tu arquitectura. Has diagnosticado correctamente que el cerebro (`OlfactoryBrain`) solo interpreta un concepto abstracto (`[forward, turn] ∈ [-1, 1]`) y que FlyGym no sabe qué significa esto [5]. 
*   La pieza que resuelve esta "incompatibilidad" es el **CPG Controller** (Central Pattern Generator) [3, 5]. 
*   El módulo `SimplifiedTripodCPG` o `AdaptiveCPGController` es el traductor: toma el comando abstracto `[f, t]` y genera de forma procedimental las trayectorias para los 42 ángulos de las articulaciones usando un patrón de marcha en trípode (alternando grupos de patas a frecuencias de 8-12 Hz) [3, 9]. Si la mosca se mueve erráticamente, debes revisar que el módulo `BrainFly` esté usando el método de mapeo *Híbrido* (que pasa por el CPG) y no un mapeo directo ("Direct mapping") que omita las fases del ciclo de marcha [6].

**5. Modularidad y actualización de `render_enhanced_3d_v2.py`**
Tu arquitectura está diseñada para ser completamente modular con cuatro niveles: Sensorial (`OdorField`), Cognitivo (`ImprovedOlfactoryBrain`), Motor (`BrainFly`/`CPG`) y Físico (`Simulation`) [5, 7].
Cuando actualices `render_enhanced_3d_v2.py`, este archivo debe actuar únicamente como el "orquestador". No debería contener lógica de física ni de toma de decisiones; simplemente debe instanciar el campo de olor, conectar el cerebro a la mosca (`BrainFly`), inicializar la simulación con el timestep correcto (0.1 ms) y manejar la renderización opcional [5, 8, 10]. Esto te permitirá mantener el modo "solo físicas" (que es mucho más rápido para pruebas) separado de la visualización [10]. Además, asegúrate de aplicar el arreglo crítico reciente de aumentar el `temporal_gradient_gain` del cerebro de 10.0 a 50.0 para mejorar la sensibilidad y la acción de avance [1, 6].



Aquí tienes el plan de diseño y arquitectura detallado, redactado con un alto nivel técnico tanto en el aspecto neurobiológico como en el computacional (ingeniería de software). 

Puedes copiar todo el bloque a continuación y guardarlo como **`data/docs/SNN_INTEGRATION_DESIGN.md`** en tu repositorio.

***

# Diseño de Integración Sensoriomotora: Fusión de SNN (Brian2) y Biomecánica (FlyGym/MuJoCo)

## 1. Fundamento Biológico y Arquitectura del Sistema
El objetivo de este módulo es reemplazar el controlador heurístico con una Red Neuronal de Picos (SNN) biológicamente fundamentada. La arquitectura modela el flujo de información desde la transducción quimiosensorial hasta la activación de los Generadores Centrales de Patrones (CPGs) en el Cordón Nervioso Ventral (VNC) [1, 2].

La vía de procesamiento implementada es:
1. **Antena (Sensórica):** Las Neuronas Sensoriales Olfativas (ORNs) detectan la concentración de odorantes [3].
2. **Lóbulo Antenal (AL - Normalización):** Las Interneuronas Locales (LNs) aplican inhibición lateral (normalización divisiva) a las Neuronas de Proyección (PNs) para separar la intensidad del olor de su identidad y hacer el sistema invariante a la concentración absoluta [4].
3. **Cuerpo Fungiforme (MB - Memoria y Codificación Esparsa):** Las células de Kenyon (KCs) reciben las señales. La neurona APL (Anterior Paired Lateral) provee retroalimentación inhibitoria global para mantener una codificación esparsa (sparse coding) [5, 6].
4. **Vía Motora Descendente (DNs):** Las señales de valencia (MBONs) convergen en las Neuronas Descendentes (DNs), que actúan como cuello de botella computacional para enviar comandos de alto nivel al VNC [1, 7].
5. **Cordón Nervioso Ventral (VNC):** Los CPGs decodifican la señal de las DNs en cinemática articular a ~10 Hz (trípode) [2].

---

## 2. Implementación de la Clase Wrapper: `SNN_OlfactoryBrain`

Este archivo servirá como puente entre la física continua de `FlyGym` y la dinámica discreta de `Brian2` [8]. 

**Ruta sugerida:** `src/controllers/snn_olfactory_brain.py`

```python
import numpy as np
from brian2 import *
from .CerebroDrosophila import CerebroDrosophila

class SNN_OlfactoryBrain:
    """
    Wrapper integrador que encapsula la simulación de picos (Brian2)
    y la interconecta con las observaciones físicas del entorno (FlyGym).
    """
    def __init__(self, dt_physics: float, dt_neural: float = 0.1*ms):
        # 1. Inicialización del modelo biológico
        self.cerebro = CerebroDrosophila(realista=True)
        
        # 2. Sincronización de Relojes (Clock Synchronization)
        # MuJoCo y Brian2 operan en escalas de tiempo diferentes.
        self.dt_physics = dt_physics * second
        defaultclock.dt = dt_neural
        
        # 3. Ventana de integración temporal para decodificación (Rate Coding)
        self.integration_window = 50 * ms 
        
    def step(self, left_odor: float, right_odor: float) -> np.ndarray:
        """
        Paso de simulación integradora.
        """
        # A. Transducción Sensorial (Concentración -> Corriente)
        self._encode_sensory_input(left_odor, right_odor)
        
        # B. Integración Dinámica (Ecuaciones Diferenciales)
        # Avanza la simulación neuronal el equivalente a un paso físico
        self.cerebro.net.run(self.dt_physics)
        
        # C. Decodificación Motora (Spikes -> Comandos de CPG)
        forward, turn = self._decode_motor_output()
        
        return np.array([forward, turn])
```

---

## 3. Transducción Sensorial: Sensilia Antenal a ORNs

La concentración matemática del campo gaussiano (`OdorField`) debe convertirse en corriente biológica inyectada (`I_ext`) en las ORNs. Para preservar la *klinotaxia* (navegación por asimetría espacial), se divide la población de ORNs topográficamente entre la antena izquierda y derecha [9].

```python
    def _encode_sensory_input(self, left_odor: float, right_odor: float):
        """
        Convierte la concentración química en estímulos eléctricos para las ORNs.
        Aplica un factor de ganancia para mapear la escala física al umbral reobásico
        de las neuronas Leaky Integrate-and-Fire (LIF) o AdEx en Brian2.
        """
        N_total = self.cerebro.N_orn
        mitad = N_total // 2
        
        # Factor de ganancia (Tuning parameter): Convierte gradiente en pAmp
        # Basado en la respuesta no lineal de las ORNs reales.
        GAIN_FACTOR = 150.0 * pamp 
        BASELINE_NOISE = 5.0 * pamp # Ruido basal para actividad espontánea
        
        # Inyección asimétrica para preservar disparidad inter-antenal
        self.cerebro.G_orn.I_ext[:mitad] = (left_odor * GAIN_FACTOR) + BASELINE_NOISE
        self.cerebro.G_orn.I_ext[mitad:] = (right_odor * GAIN_FACTOR) + BASELINE_NOISE
```

---

## 4. Decodificación Motora: DNs a CPG

El controlador `CPG` espera variables cinemáticas `[forward, turn] ∈ [-1, 1]`. En la *Drosophila* real, neuronas descendentes específicas controlan comportamientos específicos [2, 10]:
*   **DN Forward (ej. DNg02):** Aumenta la amplitud/velocidad de la marcha [11].
*   **MDN (Moonwalker):** Comanda marcha en reversa [2].
*   **DN Turn (ej. DNa01, DNa02, PFL3):** Diferencias de tasa de disparo entre los hemisferios izquierdo y derecho generan asimetría en la marcha para rotar el "heading" [10, 12].

Se utiliza un decodificador basado en tasa de disparo (Firing Rate) sobre una ventana móvil.

```python
    def _decode_motor_output(self) -> tuple:
        """
        Decodifica la tasa de disparo de la población de Neuronas Descendentes (DNs)
        para generar comandos motores continuos hacia el CPG del VNC.
        """
        spike_trains = self.cerebro.M_dn.spike_trains()
        current_time = self.cerebro.net.t
        
        def calculate_firing_rate(neuron_indices) -> float:
            """Calcula la frecuencia media (Hz) de un subgrupo en los últimos 50ms"""
            total_spikes = 0
            for idx in neuron_indices:
                spikes = spike_trains[idx]
                # Filtrar solo los spikes dentro de la ventana de integración
                recent_spikes = spikes[spikes >= (current_time - self.integration_window)]
                total_spikes += len(recent_spikes)
            
            # Frecuencia en Hz = (spikes / ventana) / numero_neuronas
            if len(neuron_indices) == 0: return 0.0
            return (total_spikes / (self.integration_window / second)) / len(neuron_indices)

        # Mapeo Biológico Hipotético de tu población G_dn:
        # Asumiendo que definiste subgrupos en CerebroDrosophila:
        # idx 0: MDN (Moonwalker / Atrás)
        # idx 1: DN_Left (Giro Izquierda - ej. PFL3_L)
        # idx 2: DN_Right (Giro Derecha - ej. PFL3_R)
        # idx 3: DN_Forward (Avance - ej. DNg02)
        
        rate_mdn     = calculate_firing_rate()
        rate_left    = calculate_firing_rate([13])
        rate_right   = calculate_firing_rate([14])
        rate_forward = calculate_firing_rate([15])
        
        MAX_FREQ_HZ = 80.0  # Frecuencia de saturación biológica esperada en DNs
        
        # 1. Cálculo de Forward/Backward (Competencia entre DNg02 y MDN)
        if rate_mdn > rate_forward:
            forward_cmd = - (rate_mdn / MAX_FREQ_HZ) # Evasión / Reversa
        else:
            forward_cmd = (rate_forward / MAX_FREQ_HZ) # Quimiotaxis positiva
            
        # 2. Cálculo de Turn (Diferencia inter-hemisférica)
        turn_cmd = (rate_right - rate_left) / MAX_FREQ_HZ
        
        # Aplicar saturación (Clipping) para estabilidad del CPG
        return np.clip(forward_cmd, -1.0, 1.0), np.clip(turn_cmd, -1.0, 1.0)
```

---

## 5. Instrucciones de Implementación y Fases de Calibración

Para integrar este código al repositorio `Mosca` sin romper la simulación actual, sigue estos pasos secuenciales:

### Fase 1: Sustitución Modular
1. Guarda el bloque de código del `SNN_OlfactoryBrain` en la carpeta `src/controllers/`.
2. En `src/controllers/brain_fly.py`, cambia la instanciación:
   ```python
   # Comenta el cerebro heurístico viejo:
   # self.brain = ImprovedOlfactoryBrain(...) 
   
   # Instancia la nueva red neuromórfica:
   from src.controllers.snn_olfactory_brain import SNN_OlfactoryBrain
   self.brain = SNN_OlfactoryBrain(dt_physics=self.sim.dt)
   ```

### Fase 2: Calibración Biológica (Tuning)
1. **Calibración Basal (Odor = 0):** Ejecuta la simulación con el olor apagado. Ajusta `BASELINE_NOISE` hasta que las DNs generen un disparo muy esporádico (ruido basal), logrando que la mosca se mantenga virtualmente quieta pero con un leve "temblor" de postura (típico estado de vigilancia).
2. **Respuesta Ortostática (Gradiente Temporal):** Enciende la pluma gaussiana. Ajusta el `GAIN_FACTOR` (pAmp) para que al entrar en el gradiente, la sub-población de PNs evite la saturación gracias a la inhibición cruzada de las LNs, resultando en una activación sostenida de `DN_Forward` pero sin pasarse a la hiperactividad (>100Hz).
3. **Respuesta Klinotáctica:** Coloca la fuente de olor a la izquierda de la mosca. Verifica que `rate_left` sea superior a `rate_right` induciendo un comando de `turn_cmd` negativo suave, haciendo que el CPG genere pasos más cortos en la extremidad izquierda (rotación hacia la fuente).
