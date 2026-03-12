# Análisis y Recomendaciones de Mejora - Proyecto Mosca

**Fecha**: 2026-03-12
**Versión**: 2.0 (Reestructurado)
**Tipo**: Análisis Técnico + Plan de Acción

---

## 📋 NOTA IMPORTANTE

Este documento ha sido **reestructurado** para alinearse con los estándares del proyecto.

**Documentos relacionados**:
- **`data/docs/ARCHITECTURE_ANALYSIS.md`** - Análisis arquitectural completo (NUEVO)
- **`data/docs/COMPLETE_CODE_REVIEW.md`** - Análisis técnico exhaustivo del código
- **`data/docs/EXECUTIVE_SUMMARY.md`** - Resumen ejecutivo del proyecto
- **`data/docs/WORKFLOW_GUIDE.md`** - Guía de uso de scripts

Este documento se enfoca en **recomendaciones de implementación** para resolver problemas del renderizado 3D.

---

## 🎯 RESUMEN EJECUTIVO

### Contexto

El proyecto implementa navegación quimiotáctica para *Drosophila melanogaster* usando FlyGym. Tiene una **arquitectura modular sólida** en `/src`, pero existen **problemas críticos** que afectan el renderizado 3D.

### Problema Principal Reportado

**"La mosca no se mueve, su cuerpo entero gira 180 grados y las patas están totalmente rectas (como un cuerpo muerto)"**

### Hallazgos Principales:

1. ✅ **Arquitectura modular bien diseñada** - Código en `/src` es sólido
2. ⚠️ **Problema crítico identificado**: Falta extracción y uso del heading (orientación) de la mosca
3. ⚠️ **Controller incorrecto en uso**: `BrainFly` usa el viejo `OlfactoryBrain` en lugar del mejorado `ImprovedOlfactoryBrain`
4. ⚠️ **Acoplamiento simulación-renderizado**: No se puede replay sin re-simular
5. ⚠️ **Archivos legacy sin integrar**: `neuromechfly_kinematic_replay.py` y `render_enhanced_3d_v2.py` en raíz

---

## 1. PROBLEMA DEL RENDERIZADO 3D: MOSCA RÍGIDA Y ROTADA

### 1.1 Descripción del Problema

Según la documentación y mi análisis del código:
- La mosca NO SE MUEVE de forma natural en el render 3D
- El cuerpo entero gira 180 grados en lugar de caminar
- Las patas están totalmente rectas (como un cuerpo muerto)

### 1.2 Causa Raíz Identificada

El problema tiene **múltiples causas interrelacionadas**:

#### A) **Falta de Extracción de Heading/Orientación**

**Ubicación**: `src/controllers/brain_fly.py:113-141`

El `ImprovedOlfactoryBrain` **REQUIERE** el parámetro `heading_radians` para funcionar correctamente:

```python
# improved_olfactory_brain.py:72-77
def step(
    self,
    odor_field,
    current_position: np.ndarray,
    heading_radians: float  # ← REQUERIDO pero nunca proporcionado
) -> np.ndarray:
```

Pero en `brain_fly.py:136`, el cerebro se llama así:

```python
motor_signal = self.brain.step(odor)  # Solo pasa concentración escalar
```

**Problema**: El cerebro antiguo (`OlfactoryBrain`) solo recibe concentración escalar, pero el mejorado necesita:
- `odor_field` (campo completo, no solo concentración)
- `current_position` (posición 3D de la mosca)
- `heading_radians` (orientación de la mosca)

Sin el heading correcto, la detección bilateral (izquierda-derecha) apunta en la **dirección incorrecta**, causando giros erróneos.

#### B) **BrainFly Usa Controller Antiguo**

**Ubicación**: Todo el workflow usa el viejo sistema

El `ImprovedOlfactoryBrain` existe y está correctamente implementado con:
- ✅ Bilateral sensing (antenas izquierda/derecha)
- ✅ Temporal gradient (dC/dt para forward)
- ✅ Parámetros biológicos validados

Pero **NADIE LO USA**. Todo el código sigue usando el `OlfactoryBrain` antiguo que:
- Solo recibe concentración escalar
- No hace detección bilateral
- No calcula temporal gradient correctamente

#### C) **Renderizado Aplica Solo Ángulos de Joints, No Orientación Corporal**

**Ubicación**: `src/rendering/core/frame_renderer.py:78-95`

```python
# frame_renderer.py:82-88
for frame_idx in range(n_frames):
    # Compilar acción para este frame
    action = {}
    for joint_name in joint_names:
        action[joint_name] = self.joint_angles[joint_name][frame_idx]

    # Ejecutar step de simulación
    obs, info = self.simulation.step(action)
```

**Problema**:
- Solo se aplican ángulos de 42 articulaciones (joints de patas)
- No se especifica la **orientación del cuerpo** (yaw/pitch/roll)
- La física de MuJoCo determina la orientación corporal basándose solo en los joints
- Sin control explícito de orientación, el cuerpo puede quedar en posiciones no naturales

### 1.3 Por Qué la Mosca Se Ve "Muerta"

Las patas están rectas porque:

1. **Datos cinemáticos incorrectos**: Si los datos guardados en `.pkl` solo contienen ángulos de joints sin contexto de movimiento, las patas no mostrarán el patrón de marcha natural
2. **Sin CPG (Central Pattern Generator)**: El rendering solo reproduce ángulos estáticos, no genera patrones de marcha
3. **Init pose problemático**: La pose inicial "stretch" puede dejar las patas extendidas si no hay suficientes datos de movimiento

El cuerpo gira 180° porque:

1. **Sin heading tracking**: La orientación no se extrae correctamente de las observaciones
2. **Bilateral sensing mal orientado**: Sin heading correcto, el cerebro calcula mal qué es "izquierda" y "derecha"
3. **Física compensa incorrectamente**: MuJoCo intenta estabilizar el cuerpo pero sin comandos de orientación correctos

---

## 2. ACOPLAMIENTO SIMULACIÓN-RENDERIZADO

### 2.1 Problema Actual

**Ubicación**: `src/rendering/core/frame_renderer.py:88`

```python
obs, info = self.simulation.step(action)  # ← Avanza física
frame = self._render_frame(frame_idx)      # ← Renderiza inmediatamente
```

**Problemas**:
1. **Un paso de física = un frame**: No se pueden renderizar múltiples frames por paso de física
2. **No hay modo replay**: No se puede renderizar una trayectoria guardada sin re-simular
3. **Tasas acopladas**: La tasa de rendering está acoplada a la tasa de física
4. **Sin separación de concernencias**: Física y renderizado mezclados en el mismo loop

### 2.2 Arquitectura Actual

```
┌─────────────────────────────────────┐
│   Simulation.step(action)           │
│   - Avanza física (10 kHz)          │
│   - Actualiza posiciones             │
│   - Calcula fuerzas                  │
└──────────────┬──────────────────────┘
               │ Immediatamente después
               ▼
┌─────────────────────────────────────┐
│   sim.render()                       │
│   - Captura frame de MuJoCo         │
│   - Un frame por step                │
└─────────────────────────────────────┘
```

### 2.3 Arquitectura Ideal (Desacoplada)

```
FASE 1: SIMULACIÓN (genera trayectoria)
┌─────────────────────────────────────┐
│   Simulation Loop                    │
│   - Ejecuta física                   │
│   - Guarda TODOS los estados:       │
│     * Posiciones de cuerpo           │
│     * Ángulos de joints              │
│     * Orientación (quaternion)       │
│     * Velocidades                    │
└──────────────┬──────────────────────┘
               │
               ▼
         trajectory.pkl
         (estado completo)

FASE 2: RENDERIZADO (reproduce trayectoria)
┌─────────────────────────────────────┐
│   Replay Renderer                    │
│   - Lee trajectory.pkl               │
│   - Restaura ESTADO COMPLETO         │
│   - Renderiza a tasa deseada        │
│   - Puede renderizar múltiples veces │
└─────────────────────────────────────┘
```

---

## 3. RECOMENDACIONES DE MEJORA

### 3.1 PRIORIDAD ALTA - Arreglar el Renderizado 3D

#### Paso 1: Extraer y Pasar Heading a ImprovedOlfactoryBrain

**Archivo a modificar**: `src/controllers/brain_fly.py`

**Cambios necesarios**:

```python
def step(self, obs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Ejecutar un paso sensoriomotor."""
    self._last_obs = obs

    # 1. Extraer posición de la cabeza
    head_pos = self._extract_head_position(obs)

    # 2. Extraer orientación (heading)
    heading = self._extract_heading(obs)  # ← NUEVO

    # 3. Procesar con cerebro MEJORADO
    if isinstance(self.brain, ImprovedOlfactoryBrain):
        # Pasar campo completo, posición y heading
        motor_signal = self.brain.step(
            self.odor_field,
            head_pos,
            heading  # ← NUEVO
        )
    else:
        # Fallback para cerebro antiguo
        odor = self.get_sensory_input(obs)
        motor_signal = self.brain.step(odor)

    # 4. Convertir señal cerebral a acciones motoras
    action = self._motor_signal_to_action(motor_signal)

    return action

def _extract_heading(self, obs: Dict[str, Any]) -> float:
    """
    Extraer orientación (yaw) de la mosca desde observaciones.

    Returns:
        float: Heading en radianes
    """
    try:
        # Opción 1: Si hay quaternion de orientación
        if "fly_orientation" in obs:
            quat = obs["fly_orientation"]
            # Convertir quaternion a yaw
            yaw = self._quaternion_to_yaw(quat)
            return yaw

        # Opción 2: Si FlyGym proporciona orientación directamente
        elif "orientation" in obs:
            return obs["orientation"][2]  # yaw

        # Opción 3: Calcular desde velocidad
        elif "fly_velocity" in obs:
            vx, vy = obs["fly_velocity"][:2]
            return np.arctan2(vy, vx)

        # Opción 4: Usar orientación almacenada
        else:
            # Mantener última orientación conocida
            return getattr(self, '_last_heading', 0.0)

    except Exception as e:
        print(f"Warning: Error extrayendo heading: {e}")
        return 0.0

def _quaternion_to_yaw(self, quat: np.ndarray) -> float:
    """Convertir quaternion a ángulo yaw."""
    # quat = [w, x, y, z] o [x, y, z, w] dependiendo de convención
    # Fórmula: yaw = atan2(2(wz + xy), 1 - 2(y² + z²))
    w, x, y, z = quat
    yaw = np.arctan2(2.0 * (w * z + x * y),
                     1.0 - 2.0 * (y * y + z * z))
    return yaw
```

#### Paso 2: Usar ImprovedOlfactoryBrain en Todo el Código

**Archivos a modificar**:
- `tools/run_complete_3d_simulation.py`
- Cualquier script que cree `BrainFly`

**Cambio**:
```python
# ANTES:
from src.controllers.olfactory_brain import OlfactoryBrain
brain = OlfactoryBrain(...)

# DESPUÉS:
from src.controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
brain = ImprovedOlfactoryBrain(
    bilateral_distance=1.2,  # mm (distancia real entre antenas)
    forward_scale=1.0,
    turn_scale=0.8,
    threshold=0.01,
    temporal_gradient_gain=10.0
)
```

#### Paso 3: Guardar Estado Completo en Simulación

**Archivo a modificar**: `src/simulation/olfactory_sim.py`

**Cambios necesarios**:

```python
def step(self, obs: Dict[str, Any], physics_steps: int = 1):
    """Ejecutar paso con logging completo."""

    # ... código existente ...

    # MEJORAR LOGGING: Guardar estado completo
    state = {
        'timestamp': current_time,
        'position': head_pos,  # [x, y, z]
        'orientation': self._extract_orientation(obs),  # [roll, pitch, yaw] o quaternion
        'joint_angles': self._extract_all_joints(obs),  # Todos los 42 DoF
        'body_velocity': self._extract_velocity(obs),  # [vx, vy, vz]
        'odor_concentration': odor_conc,
        'motor_commands': action,  # [forward, turn]
    }

    self.trajectory.append(state)

    # ... resto del código ...
```

#### Paso 4: Mejorar Frame Renderer para Restaurar Estado Completo

**Archivo a modificar**: `src/rendering/core/frame_renderer.py`

**Cambios necesarios**:

```python
def _compile_action_from_state(self, state: Dict) -> Dict:
    """
    Compilar acción que incluye joints Y orientación corporal.

    Args:
        state: Estado completo con position, orientation, joints

    Returns:
        Dict con comandos para FlyGym incluyendo orientación
    """
    action = {}

    # 1. Ángulos de joints (como antes)
    for joint_name, angle in state['joint_angles'].items():
        action[joint_name] = angle

    # 2. NUEVO: Orientación corporal (si FlyGym lo soporta)
    if 'body_orientation' in action:
        action['body_orientation'] = state['orientation']

    # 3. NUEVO: Posición corporal (para forzar posición correcta)
    if 'body_position' in action:
        action['body_position'] = state['position']

    return action
```

**NOTA**: FlyGym puede no soportar directamente comandos de orientación corporal. En ese caso, necesitaremos:
- Investigar API de FlyGym para control de posición/orientación
- O usar un approach diferente: configurar el estado del simulador directamente

### 3.2 PRIORIDAD ALTA - Desacoplar Simulación de Renderizado

#### Approach Recomendado:

**Crear Dos Modos de Operación**:

1. **Modo Simulación** (genera datos)
   - Ejecuta física sin renderizado
   - Guarda trayectoria completa con estado detallado
   - Rápido, puede correr en servidor sin GPU

2. **Modo Replay** (renderiza datos)
   - Lee trayectoria guardada
   - Restaura estados y renderiza
   - Puede renderizar a diferentes tasas (30fps, 60fps, 120fps)
   - Puede renderizar múltiples veces sin re-simular

**Implementación**:

```python
# Nuevo archivo: src/rendering/replay_renderer.py

class ReplayRenderer:
    """
    Renderizador que reproduce trayectorias guardadas.

    Desacoplado de la simulación - solo lee estados y renderiza.
    """

    def __init__(self, trajectory_file: str):
        """Cargar trayectoria guardada."""
        with open(trajectory_file, 'rb') as f:
            self.trajectory = pickle.load(f)

    def render_to_video(
        self,
        output_file: str,
        fps: int = 60,
        camera_config: Dict = None
    ):
        """
        Renderizar trayectoria completa a video.

        Args:
            output_file: Archivo de salida MP4
            fps: Frames por segundo del video
            camera_config: Configuración de cámara
        """
        # 1. Setup FlyGym environment (sin física)
        sim = self._setup_kinematic_sim()

        # 2. Para cada estado en la trayectoria
        frames = []
        for state in self.trajectory:
            # Restaurar estado completo
            self._restore_state(sim, state)

            # Renderizar frame
            frame = sim.render()
            frames.append(frame)

        # 3. Guardar video
        save_video(frames, output_file, fps=fps)

    def _restore_state(self, sim, state: Dict):
        """Restaurar estado completo del simulador."""
        # Establecer posición y orientación del cuerpo
        sim.set_body_position(state['position'])
        sim.set_body_orientation(state['orientation'])

        # Establecer ángulos de joints
        for joint_name, angle in state['joint_angles'].items():
            sim.set_joint_angle(joint_name, angle)
```

**Uso**:

```python
# 1. Ejecutar simulación (SIN renderizado)
from src.simulation import OlfactorySimulation

sim = OlfactorySimulation(brain_fly, odor_field)
sim.setup(use_rendering=False)  # ← Sin renderizado
sim.run(duration=10.0)
sim.save_trajectory("outputs/traj_001.pkl")  # Guarda todo

# 2. Renderizar después (tantas veces como quieras)
from src.rendering import ReplayRenderer

renderer = ReplayRenderer("outputs/traj_001.pkl")
renderer.render_to_video("outputs/video_60fps.mp4", fps=60)
renderer.render_to_video("outputs/video_30fps.mp4", fps=30)
renderer.render_to_video("outputs/video_slowmo.mp4", fps=120)
```

### 3.3 PRIORIDAD MEDIA - Mejoras Arquitecturales

#### A) Separar Lógica de Control de Física

**Crear módulo de control independiente**:

```python
# Nuevo archivo: src/controllers/control_layer.py

class ControlLayer:
    """
    Capa de control separada de la física.

    Maneja:
    - Extracción de estados sensoriales
    - Llamada a cerebro/controller
    - Generación de comandos motores

    NO maneja:
    - Física (eso es simulación)
    - Renderizado (eso es rendering)
    """

    def __init__(self, brain, odor_field):
        self.brain = brain
        self.odor_field = odor_field

    def compute_action(
        self,
        position: np.ndarray,
        orientation: float
    ) -> np.ndarray:
        """
        Computar acción basada solo en estado sensorial.

        Args:
            position: Posición 3D actual
            orientation: Orientación (yaw) actual

        Returns:
            np.ndarray: [forward, turn]
        """
        # Llamar al cerebro con información completa
        motor_signal = self.brain.step(
            self.odor_field,
            position,
            orientation
        )

        return motor_signal
```

**Beneficio**: El control está completamente separado de la física. Se puede:
- Testear el control sin ejecutar física
- Usar el mismo control en diferentes simuladores
- Replay control decisions offline

#### B) Crear Pipeline de Procesamiento

```python
# Nuevo archivo: src/core/pipeline.py

class SimulationPipeline:
    """
    Pipeline que orquesta: sensado → control → actuación → física.
    """

    def __init__(self, components: Dict):
        self.sensor = components['sensor']
        self.controller = components['controller']
        self.motor = components['motor']
        self.physics = components['physics']

    def step(self):
        """Un paso completo del pipeline."""
        # 1. SENSADO
        sensory_input = self.sensor.read()

        # 2. CONTROL (completamente separado)
        motor_command = self.controller.compute(sensory_input)

        # 3. MOTOR (conversión a comandos de bajo nivel)
        joint_commands = self.motor.convert(motor_command)

        # 4. FÍSICA (ejecutar comandos)
        new_state = self.physics.step(joint_commands)

        return new_state
```

### 3.4 PRIORIDAD BAJA - Refactorings Opcionales

#### A) Parámetros Biológicos

Actualizar parámetros para coincidir con documentación:

**Archivo**: `src/controllers/improved_olfactory_brain.py:38`

```python
# ACTUAL:
bilateral_distance: float = 2.0,  # ← Muy grande

# RECOMENDADO:
bilateral_distance: float = 1.2,  # mm (real Drosophila antenna width)
```

**Impacto**: Gradiente bilateral más realista, giros más naturales

#### B) Documentar Mapeo de Velocidades

**Archivo**: `README.md` o `src/controllers/improved_olfactory_brain.py`

Documentar claramente:
```python
# forward_scale=1.0 corresponde a:
# - forward=1.0 → 10 mm/s (velocidad típica de Drosophila)
# - forward=0.5 → 5 mm/s
# - forward=0.0 → detenida
```

---

## 4. PLAN DE IMPLEMENTACIÓN SUGERIDO

### Fase 1: Arreglar Renderizado (1-2 días)

**Objetivo**: Que la mosca se mueva correctamente en 3D

1. ✅ Implementar extracción de heading en `brain_fly.py`
2. ✅ Modificar todos los scripts para usar `ImprovedOlfactoryBrain`
3. ✅ Mejorar logging para guardar estado completo (posición + orientación + joints)
4. ✅ Testear renderizado con datos mejorados
5. ✅ Verificar que la mosca camina naturalmente (no gira 180°, patas se mueven)

**Criterio de éxito**: Video 3D muestra mosca caminando con patrón de marcha natural

### Fase 2: Desacoplar Simulación y Renderizado (2-3 días)

**Objetivo**: Separar generación de datos de visualización

1. ✅ Crear `ReplayRenderer` para renderizar trayectorias guardadas
2. ✅ Modificar `OlfactorySimulation` para tener modo "sin renderizado"
3. ✅ Implementar restauración de estado completo en renderer
4. ✅ Testear pipeline: simular → guardar → renderizar múltiples veces
5. ✅ Documentar nuevos workflows

**Criterio de éxito**: Poder simular 1 vez y renderizar N veces a diferentes FPS

### Fase 3: Refactoring Arquitectural (3-5 días - OPCIONAL)

**Objetivo**: Arquitectura más limpia y mantenible

1. ✅ Crear `ControlLayer` separado
2. ✅ Crear `SimulationPipeline` para orquestar componentes
3. ✅ Separar claramente: sensado / control / actuación / física / renderizado
4. ✅ Actualizar tests
5. ✅ Actualizar documentación

**Criterio de éxito**: Cada componente es testeable independientemente

---

## 5. CÓMO PROCEDER (APPROACH)

### Opción A: Empezar con lo Mínimo (RECOMENDADO)

**Enfoque incremental** - arreglar solo el problema inmediato:

1. **Día 1**: Arreglar extracción de heading
   - Modificar `brain_fly.py` para extraer orientación
   - Pasar heading a `ImprovedOlfactoryBrain`
   - Testear que bilateral sensing funciona correctamente

2. **Día 2**: Mejorar logging y renderizado
   - Guardar orientación en trayectorias
   - Restaurar orientación en renderer
   - Generar video 3D y verificar

3. **Día 3**: Optimizar y documentar
   - Ajustar parámetros si necesario
   - Documentar cambios
   - Crear ejemplos

**Ventajas**:
- ✅ Solución rápida al problema inmediato
- ✅ Cambios mínimos, bajo riesgo
- ✅ Resultados visibles en 1-2 días

**Desventajas**:
- ⚠️ No resuelve acoplamiento simulación-renderizado
- ⚠️ Arquitectura sigue siendo mejorable

### Opción B: Refactoring Completo

**Enfoque arquitectural** - rediseñar para mejor mantenibilidad:

1. **Semana 1**: Separar completamente simulación y renderizado
2. **Semana 2**: Crear pipeline modular
3. **Semana 3**: Refactorizar código existente
4. **Semana 4**: Tests y documentación

**Ventajas**:
- ✅ Arquitectura mucho más limpia
- ✅ Más fácil mantener y extender
- ✅ Componentes desacoplados y testeables

**Desventajas**:
- ⚠️ Mucho más trabajo (3-4 semanas)
- ⚠️ Mayor riesgo de romper cosas existentes
- ⚠️ Requiere re-testing extensivo

### Opción C: Híbrido (RECOMENDADO PARA LARGO PLAZO)

**Enfoque pragmático** - arreglar ahora, mejorar después:

1. **Corto plazo (esta semana)**: Implementar Opción A
   - Arreglar problema de renderizado
   - Funcionalidad básica operativa

2. **Mediano plazo (próximo mes)**: Implementar desacoplamiento
   - Crear `ReplayRenderer`
   - Separar simulación de renderizado
   - Mejorar workflows

3. **Largo plazo (próximos 2-3 meses)**: Refactoring arquitectural
   - Pipeline modular
   - Componentes desacoplados
   - Tests extensivos

**Ventajas**:
- ✅ Solución rápida al problema urgente
- ✅ Mejora incremental sin romper nada
- ✅ Evolución natural hacia arquitectura ideal

---

## 6. PREGUNTAS PARA DECIDIR APPROACH

Antes de proceder, considera:

1. **¿Qué es más urgente?**
   - ¿Necesitas que el renderizado funcione YA? → Opción A
   - ¿Tienes tiempo para mejorar arquitectura? → Opción B o C

2. **¿Cuál es el plan a largo plazo del proyecto?**
   - ¿Prototipo/demo? → Opción A suficiente
   - ¿Proyecto de investigación a largo plazo? → Opción C
   - ¿Producto que otros usarán? → Opción B

3. **¿Cuánto tiempo/recursos hay disponibles?**
   - 1-2 días → Opción A
   - 1-2 semanas → Opción C (fase 1-2)
   - 1+ mes → Opción B completa

4. **¿Qué cambios son más valiosos?**
   - Solo que funcione el 3D → Focus en heading y ImprovedOlfactoryBrain
   - Quieres renderizar múltiples veces → Focus en desacoplamiento
   - Mantenibilidad a largo plazo → Focus en arquitectura modular

---

## 7. INVESTIGACIÓN ADICIONAL NECESARIA

Para implementar completamente las soluciones, necesitamos:

### A) API de FlyGym para Control de Orientación

**Preguntas**:
- ¿FlyGym permite establecer orientación corporal directamente?
- ¿Cómo se representa la orientación en FlyGym? (quaternion, euler, rotation matrix?)
- ¿Se puede "forzar" una pose específica del cuerpo?

**Dónde investigar**:
- Documentación de FlyGym
- Código fuente de `flygym.Simulation`
- Ejemplos de FlyGym que controlan orientación

### B) Formato de Observaciones de FlyGym

**Preguntas**:
- ¿Qué claves contiene el diccionario `obs`?
- ¿Dónde está la orientación del cuerpo? (`obs["orientation"]`, `obs["Nuro"]["orientation"]`, etc?)
- ¿En qué formato? (quaternion [w,x,y,z], euler [roll,pitch,yaw])

**Cómo investigar**:
```python
# Crear simulación simple y examinar obs
sim = Simulation([fly], ...)
obs, info = sim.reset()
print("Claves en obs:", obs.keys())
for key, value in obs.items():
    print(f"{key}: {type(value)}, shape={getattr(value, 'shape', 'N/A')}")
```

### C) Patrón de Marcha Natural (CPG)

**Preguntas**:
- ¿Los datos guardados incluyen patrón de marcha natural?
- ¿O solo ángulos estáticos de joints?
- ¿FlyGym tiene CPG incorporado para generar marcha?

**Si no hay CPG**:
- Necesitaremos implementar generador de marcha
- O usar datos de marcha real de Drosophila
- O confiar en que FlyGym genera marcha a partir de comandos de alto nivel

---

## 8. CÓDIGO DE EJEMPLO PARA DEBUGGING

### Debug 1: Examinar Observaciones de FlyGym

```python
#!/usr/bin/env python3
"""Debug script para examinar estructura de observaciones de FlyGym."""

from flygym import Fly, Simulation
import numpy as np

# Crear mosca y simulación simple
fly = Fly(init_pose="stretch", actuated_joints="all")
sim = Simulation([fly])

# Reset y obtener observaciones
obs, info = sim.reset()

print("="*60)
print("ESTRUCTURA DE OBSERVACIONES")
print("="*60)

def print_nested_dict(d, indent=0):
    """Imprimir diccionario anidado recursivamente."""
    for key, value in d.items():
        print("  " * indent + f"{key}:")
        if isinstance(value, dict):
            print_nested_dict(value, indent + 1)
        elif isinstance(value, np.ndarray):
            print("  " * (indent + 1) + f"ndarray, shape={value.shape}, dtype={value.dtype}")
            if value.size <= 10:
                print("  " * (indent + 1) + f"values: {value}")
        else:
            print("  " * (indent + 1) + f"{type(value)}: {value}")

print_nested_dict(obs)

print("\n" + "="*60)
print("BUSCANDO ORIENTACIÓN")
print("="*60)

# Buscar campos que puedan contener orientación
orientation_candidates = []
for key, value in obs.items():
    if 'orient' in key.lower():
        orientation_candidates.append(key)
    if 'quat' in key.lower():
        orientation_candidates.append(key)
    if 'rotation' in key.lower():
        orientation_candidates.append(key)
    if isinstance(value, dict):
        for subkey in value.keys():
            if 'orient' in subkey.lower() or 'quat' in subkey.lower():
                orientation_candidates.append(f"{key}.{subkey}")

print("Candidatos para orientación:")
for candidate in orientation_candidates:
    print(f"  - {candidate}")
```

### Debug 2: Testear Extracción de Heading

```python
#!/usr/bin/env python3
"""Test heading extraction."""

from src.controllers.brain_fly import BrainFly
from src.controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from src.olfaction.odor_field import OdorField
from flygym import Fly, Simulation
import numpy as np

# Setup
odor_field = OdorField(sources=[(50, 50, 5)], sigma=10.0)
brain = ImprovedOlfactoryBrain()
brain_fly = BrainFly(brain, odor_field)

# Crear simulación
sim = Simulation([brain_fly])
obs, info = sim.reset()

print("="*60)
print("TEST: EXTRACCIÓN DE HEADING")
print("="*60)

# Intentar extraer heading
try:
    heading = brain_fly._extract_heading(obs)
    print(f"✓ Heading extraído: {heading:.4f} rad ({np.degrees(heading):.1f}°)")
except Exception as e:
    print(f"✗ Error extrayendo heading: {e}")

# Ejecutar algunos pasos y ver si heading cambia
print("\nExecutando 10 pasos y monitoreando heading:")
for i in range(10):
    action = brain_fly.step(obs)
    obs, reward, done, truncated, info = sim.step(action)

    try:
        heading = brain_fly._extract_heading(obs)
        print(f"  Step {i}: heading = {np.degrees(heading):6.1f}°")
    except:
        print(f"  Step {i}: ERROR")
```

### Debug 3: Verificar Datos Guardados

```python
#!/usr/bin/env python3
"""Verificar qué contienen los archivos .pkl de trayectorias."""

import pickle
from pathlib import Path

# Buscar primer archivo .pkl
pkl_files = list(Path("outputs").rglob("*.pkl"))
if not pkl_files:
    print("No se encontraron archivos .pkl")
    exit()

pkl_file = pkl_files[0]
print(f"Examinando: {pkl_file}")

# Cargar y examinar
with open(pkl_file, 'rb') as f:
    data = pickle.load(f)

print(f"\nTipo de datos: {type(data)}")

if isinstance(data, dict):
    print(f"Claves en datos: {list(data.keys())}")
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            print(f"\n{key}: lista de {len(value)} elementos")
            print(f"  Primer elemento: {type(value[0])}")
            if isinstance(value[0], dict):
                print(f"  Claves: {list(value[0].keys())}")
elif isinstance(data, list):
    print(f"Lista de {len(data)} elementos")
    if len(data) > 0:
        print(f"Primer elemento: {type(data[0])}")
        if isinstance(data[0], dict):
            print(f"Claves: {list(data[0].keys())}")
```

---

## 9. RESUMEN Y PRÓXIMOS PASOS

### Problemas Identificados

1. ✅ **Heading no extraído ni usado** → Bilateral sensing apunta mal
2. ✅ **Controller antiguo en uso** → No se aprovecha ImprovedOlfactoryBrain
3. ✅ **Estado incompleto en logging** → Falta orientación en datos guardados
4. ✅ **Renderizado sin orientación** → Cuerpo queda en posición no natural
5. ✅ **Simulación acoplada a renderizado** → No se puede renderizar múltiples veces

### Soluciones Propuestas (Prioridad)

**ALTA**:
1. Extraer y pasar heading a ImprovedOlfactoryBrain
2. Usar ImprovedOlfactoryBrain en todos los scripts
3. Guardar estado completo (posición + orientación + joints)
4. Restaurar estado completo en renderizado

**MEDIA**:
5. Desacoplar simulación de renderizado (ReplayRenderer)
6. Crear workflows: simular → guardar → renderizar N veces

**BAJA**:
7. Refactoring arquitectural completo (pipeline modular)
8. Actualizar parámetros biológicos
9. Documentar mapeo de velocidades

### Mi Recomendación

**Empezar con Opción A** (arreglo mínimo, 1-2 días):
- Implementar extracción de heading
- Usar ImprovedOlfactoryBrain
- Mejorar logging y renderizado
- Verificar que funciona

**Luego evaluar**:
- Si funciona bien → Dejar así o hacer Opción C (mejora incremental)
- Si sigue habiendo problemas → Investigar API de FlyGym más a fondo

**Preguntas para el usuario**:
1. ¿Cuál es la urgencia? (días, semanas, meses)
2. ¿Hay ejemplos de videos 3D correctos para comparar?
3. ¿Se puede compartir un archivo .pkl de trayectoria para examinar?
4. ¿Qué versión exacta de FlyGym se está usando?

---

## CONCLUSIÓN

El problema del renderizado 3D es **solucionable** con cambios focalizados. La causa raíz es la **falta de extracción y uso de orientación corporal** en el pipeline sensoriomotor.

Con los cambios propuestos en Fase 1 (1-2 días), el renderizado debería mostrar una mosca caminando naturalmente. El desacoplamiento completo (Fase 2) es deseable pero no urgente si solo necesitas que funcione el 3D.

**Siguiente paso recomendado**: Implementar extracción de heading en `brain_fly.py` y testear con un video corto.
