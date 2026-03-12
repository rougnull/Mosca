# Diagnóstico: Problemas de Renderizado 3D

**Fecha**: 2026-03-12
**Estado**: 🔍 DIAGNÓSTICO COMPLETO
**Problema**: La mosca se hunde en el suelo, rota 180° y se mueve a ~1 fps

---

## 🎯 RESUMEN EJECUTIVO

### Síntomas Observados:
- ✗ La mosca aparece moviéndose a 1 frame por segundo
- ✗ Rota progresivamente hasta llegar a ~180° respecto al suelo
- ✗ Se hunde en el suelo hasta atravesarlo completamente
- ✗ El cuerpo aparece rígido sin articulación natural de patas

### Root Cause Identificado:
**ARQUITECTURA HÍBRIDA INCORRECTA**: Separación entre simulación cinemática y renderizado físico

---

## 🔍 ANÁLISIS DETALLADO

### 1. Arquitectura Actual (PROBLEMÁTICA)

```
┌─────────────────────────────────────────────────────────────┐
│  run_complete_3d_simulation.py                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                              │
│  [CompleteOlfactorySimulation]                              │
│                                                              │
│  1. Simulación Cinemática (SIN FÍSICA):                     │
│     • pos += velocity * cos(heading) * dt                   │
│     • heading += angular_velocity * dt                      │
│     • Z siempre constante (línea 259): 0.0 ← PROBLEMA #1   │
│                                                              │
│  2. Generación de ángulos SINTÉTICOS:                       │
│     • Senos/cosenos simples (líneas 215-227)               │
│     • NO considera física real                              │
│     • NO considera contacto con suelo ← PROBLEMA #2         │
│                                                              │
│  3. Guardar a PKL:                                          │
│     • positions (N, 3) - cinemático                         │
│     • headings (N,) - cinemático                            │
│     • joint_angles - sintético                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    [PKL FILE]
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  src/rendering/core/mujoco_renderer.py                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                         │
│                                                              │
│  [MuJoCoRenderer]                                           │
│                                                              │
│  1. Crea FlyGym con FÍSICA COMPLETA de MuJoCo               │
│  2. Trata de aplicar ángulos cinemáticos                    │
│  3. El motor físico RECHAZA las posiciones:                 │
│     • Los ángulos no son físicamente válidos                │
│     • Las patas no soportan el peso                         │
│     • El cuerpo colapsa ← PROBLEMA #3                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘

CONFLICTO: Datos cinemáticos → Motor físico realista
```

---

## 🐛 PROBLEMAS ESPECÍFICOS

### Problema #1: Z Constante en Simulación Cinemática

**Archivo**: `tools/run_complete_3d_simulation.py:256-260`

```python
new_pos = self.pos + self.sim_dt * linear_velocity * np.array([
    np.cos(self.heading),
    np.sin(self.heading),
    0.0  # ← PROBLEMA: Z nunca cambia
])
```

**Por qué causa hundimiento**:
- La simulación cinemática asume Z=constante (no gravedad, no suelo)
- Cuando MuJoCoRenderer aplica estos datos a FlyGym:
  - FlyGym SÍ tiene gravedad y colisiones
  - Las patas NO están generando suficiente fuerza para soportar el peso
  - El cuerpo colapsa y se hunde

### Problema #2: Ángulos Articulares Sintéticos

**Archivo**: `tools/run_complete_3d_simulation.py:153-229`

```python
def _generate_joint_angles_for_step(self, step_idx, forward_cmd, turn_cmd):
    # PROBLEMA: Ángulos basados en senos/cosenos simples
    angles[f"joint_{leg}Coxa"] = 0.3 * amplitude_scale * np.sin(adjusted_phase - np.pi/4)
    angles[f"joint_{leg}Femur"] = -0.8 + 0.6 * amplitude_scale * np.sin(adjusted_phase)
    angles[f"joint_{leg}Tibia"] = 1.2 + 0.5 * amplitude_scale * np.cos(adjusted_phase)
    # ...
```

**Por qué causa problemas**:
1. **No considera dinámica real**: Las patas necesitan generar fuerza para:
   - Soportar el peso del cuerpo
   - Mantener contacto con el suelo
   - Coordinar swing/stance phases

2. **Valores fijos de offset**:
   - `Femur = -0.8 + ...`: Este offset puede no ser válido para FlyGym
   - `Tibia = 1.2 + ...`: Puede causar sobreextensión o colapso

3. **No hay feedback del suelo**: En física real, las patas ajustan su posición basado en:
   - Contacto con superficie
   - Fuerzas de reacción
   - Balance del centro de masa

### Problema #3: Rotación 180° Progresiva

**Causa raíz**: Desequilibrio entre cinemática y física

Cuando MuJoCoRenderer intenta aplicar los ángulos:
1. **Frame 1**: Fly está en postura "stretch" (válida)
2. **Frame 2-10**: Aplica ángulos sintéticos → cuerpo empieza a desequilibrarse
3. **Frame 10+**: Sin soporte de patas adecuado → cuerpo rota por gravedad
4. **Frame 50+**: Rotación completa ~180° → mosca "muerta" boca arriba

**Archivo**: `src/rendering/core/mujoco_renderer.py:168-204`

El renderer hace transición suave (smooth transition) pero esto NO soluciona el problema fundamental: los ángulos no son físicamente válidos.

```python
# Líneas 174-185: Smooth transition
if frame_idx < transition_frames:
    blend_factor = frame_idx / max(1, transition_frames - 1)
    # Problema: blend entre "stretch" (válido) y ángulos sintéticos (inválidos)
    smoothed_val = val * blend_factor
```

### Problema #4: 1 FPS Aparente

**Posible causa**: Dos explicaciones:

1. **Skip inicial de frames** (`mujoco_renderer.py:208-211`):
   ```python
   skip_initial_frames = 10  # Saltar primeros 10 frames
   if frame_idx < skip_initial_frames:
       frames_skipped += 1
       continue
   ```
   Esto puede causar que se vean menos frames de los esperados.

2. **Timestep mismatch**:
   - Simulación: dt=0.01s (100 Hz)
   - Renderizado: fps=60
   - Si hay 1500 frames de simulación → 15s @ 100Hz
   - Pero renderizado @ 60fps → 25s de video
   - Si solo se renderizan algunos frames por problemas físicos → parece lento

---

## 📊 COMPARACIÓN: CINEMÁTICA vs FÍSICA

| Aspecto | Simulación Cinemática (ACTUAL) | Simulación Física (NECESARIA) |
|---------|-------------------------------|-------------------------------|
| **Motor** | Integración manual de pos/heading | MuJoCo physics engine |
| **Gravedad** | ❌ No | ✅ Sí (9.81 m/s²) |
| **Contacto suelo** | ❌ No | ✅ Sí (colisiones detectadas) |
| **Fuerzas en patas** | ❌ No (solo ángulos) | ✅ Sí (torques/fuerzas calculados) |
| **Balance corporal** | ❌ No | ✅ Sí (centro de masa considerado) |
| **Ángulos válidos** | ⚠️ Sintéticos (pueden ser inválidos) | ✅ Físicamente válidos |
| **Z posición** | ❌ Constante (0.0 siempre) | ✅ Dinámica (sube/baja según patas) |
| **Orientación cuerpo** | ⚠️ Solo heading (yaw) | ✅ Completa (roll, pitch, yaw) |

---

## ✅ SOLUCIONES PROPUESTAS

### Opción A: Usar FlyGym Desde el Principio (RECOMENDADO)

**Enfoque**: Reescribir `run_complete_3d_simulation.py` para usar FlyGym con física completa.

**Implementación**:

```python
# tools/run_complete_3d_simulation_v2.py

from flygym import Fly, SingleFlySimulation
from flygym.arena import FlatTerrain
from controllers.brain_fly import BrainFly
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain

class PhysicsBasedOlfactorySimulation:
    """Simulación con física REAL de FlyGym desde el inicio."""

    def __init__(self, odor_source, duration, dt):
        # Crear FlyGym fly con física
        self.fly = Fly(
            init_pose="stretch",
            actuated_joints=all_leg_dofs,
            control="position"
        )

        # Crear arena con física
        self.arena = FlatTerrain()

        # Crear simulación con física
        self.sim = SingleFlySimulation(
            fly=self.fly,
            arena=self.arena
        )

        # Crear cerebro
        brain = ImprovedOlfactoryBrain(...)
        self.brain_fly = BrainFly(
            brain=brain,
            odor_field=OdorField(sources=odor_source, ...)
        )

        # Reset para obtener obs inicial
        self.obs, self.info = self.sim.reset()

    def step(self):
        """Ejecutar paso con física real."""
        # 1. Cerebro decide acción basado en observaciones REALES de FlyGym
        action = self.brain_fly.step(self.obs)

        # 2. Aplicar acción al simulador (con física)
        self.obs = self.sim.step(action)

        # 3. Renderizar frame actual
        frame = self.sim.render()

        return frame
```

**Ventajas**:
- ✅ Física correcta desde el inicio
- ✅ No hay mismatch cinemática-física
- ✅ Ángulos siempre físicamente válidos
- ✅ Z posición calculada correctamente
- ✅ Orientación corporal completa (roll, pitch, yaw)
- ✅ Balance y contacto con suelo automáticos

**Desventajas**:
- ⚠️ Requiere reescribir `run_complete_3d_simulation.py`
- ⚠️ Más lento computacionalmente (física realista)
- ⚠️ Necesita `_motor_signal_to_action()` en BrainFly para convertir [forward, turn] → joint angles

### Opción B: Mejorar Generación de Ángulos Cinemáticos

**Enfoque**: Mejorar `_generate_joint_angles_for_step()` para que genere ángulos físicamente plausibles.

**Cambios necesarios**:

1. **Usar inverse kinematics**:
   - Especificar posiciones deseadas de las patas (en espacio cartesiano)
   - Calcular ángulos articulares necesarios para alcanzar esas posiciones
   - Esto garantiza que las patas toquen el suelo

2. **Considerar stance/swing phases**:
   ```python
   # Stance phase: pata en el suelo, soportando peso
   if in_stance_phase:
       # Pata debe estar extendida y en contacto con Z=0
       foot_target_z = 0.0
       # Generar fuerzas de soporte
   else:  # Swing phase
       # Pata levantada, moviéndose hacia adelante
       foot_target_z = 2.0  # Altura de elevación
   ```

3. **Actualizar Z dinámicamente**:
   ```python
   # En lugar de Z=0.0 constante:
   body_height = calculate_body_height_from_legs(current_leg_angles)
   new_pos[2] = body_height
   ```

**Ventajas**:
- ✅ Mantiene arquitectura actual (solo mejoras)
- ✅ Más rápido que física completa

**Desventajas**:
- ❌ Sigue siendo aproximación (no física real)
- ❌ Difícil de hacer correctamente (IK no trivial)
- ❌ No garantiza estabilidad física
- ❌ Puede seguir teniendo problemas en MuJoCoRenderer

### Opción C: Híbrido - Cinemática para Navegación + Física para Renderizado

**Enfoque**: Separar navegación de renderizado completamente.

1. **Navegación**: Cinemática simple (como ahora)
   - Rápido y simple
   - Solo para decidir DÓNDE va la mosca

2. **Renderizado**: Usar FlyGym con física
   - Ignorar posiciones del PKL
   - Solo usar comandos de cerebro (forward, turn)
   - Dejar que FlyGym calcule posiciones/ángulos

**Implementación**:
```python
# MuJoCoRenderer - modo "comandos"
def render_from_commands(self, brain_actions):
    """Renderizar desde comandos de cerebro, no posiciones."""
    for forward, turn in brain_actions:
        # Convertir comandos a ángulos FlyGym
        action = self._commands_to_flygym_action(forward, turn)

        # Aplicar a simulación con física
        obs = self.sim.step(action)

        # Renderizar frame
        frame = self.sim.render()
```

**Ventajas**:
- ✅ Navegación rápida (cinemática)
- ✅ Renderizado físicamente correcto
- ✅ Separa concerns correctamente

**Desventajas**:
- ⚠️ Trayectoria renderizada puede diferir de trayectoria cinemática
- ⚠️ Necesita implementar `_commands_to_flygym_action()`

---

## 🎯 RECOMENDACIÓN

### ⭐ SOLUCIÓN RECOMENDADA: **Opción A - Física desde el Principio**

**Razones**:
1. **Correctitud**: Es la única forma de garantizar física correcta
2. **Simplicidad conceptual**: Una sola fuente de verdad (FlyGym)
3. **Mantenibilidad**: No hay sincronización cinemática-física
4. **Extensibilidad**: Permite agregar terreno complejo, obstáculos, etc.

**Pasos de implementación**:

1. **Crear `BrainFly._motor_signal_to_action()`** que convierte [forward, turn] → FlyGym action
2. **Reescribir `run_complete_3d_simulation.py`** para usar FlyGym desde inicio
3. **Eliminar generación sintética de ángulos** (dejar que FlyGym lo haga)
4. **Renderizar directamente** desde la misma simulación

---

## 🔧 ARCHIVOS A MODIFICAR

### Para Opción A (Recomendado):

1. **`src/controllers/brain_fly.py`**:
   - ✅ Ya tiene `_extract_heading()` y `_extract_head_position()`
   - ⚠️ Falta: `_motor_signal_to_action()` para convertir [forward, turn] → joint angles

2. **`tools/run_complete_3d_simulation_v2.py`** (NUEVO):
   - Implementar `PhysicsBasedOlfactorySimulation`
   - Usar FlyGym con física desde el inicio
   - Guardar frames directamente (no PKL intermedio)

3. **`src/rendering/core/mujoco_renderer.py`** (OPCIONAL):
   - Puede simplificarse si todo se hace en FlyGym
   - O adaptarse para modo "live rendering"

---

## 📝 NOTAS TÉCNICAS

### Sobre _motor_signal_to_action()

Esta función necesita mapear comandos abstractos [forward, turn] a ángulos articulares específicos de FlyGym.

**Opciones**:

1. **Usar CPG (Central Pattern Generator)** como en los ejemplos de FlyGym:
   ```python
   from flygym.preprogrammed import get_cpg_biased_controller

   controller = get_cpg_biased_controller(
       forward_velocity=forward * max_speed,
       turn_rate=turn * max_turn
   )
   action = controller.step()
   ```

2. **Usar ángulos pre-programados** (tripod gait):
   ```python
   def _motor_signal_to_action(self, motor_signal):
       forward, turn = motor_signal

       # Usar pattern generator interno de FlyGym
       # o implementar tripod gait manualmente
       joint_angles = self._tripod_gait_angles(forward, turn, self.phase)
       return {"joints": joint_angles}
   ```

### Sobre Performance

Simulación con física completa es ~10-50x más lenta que cinemática:
- Cinemática: 1500 steps en ~1 segundo
- Física (FlyGym): 1500 steps en ~10-30 segundos

**Mitigación**:
- Usar `sim_dt` más grande (0.02s en lugar de 0.01s)
- Reducir duración de simulación para testing (5s en lugar de 15s)
- Usar `subsample` al renderizar

---

## 🔗 REFERENCIAS

- **FlyGym Documentation**: https://neuromechfly.org/api_ref/simulation.html
- **CPG Controllers**: `flygym.preprogrammed.get_cpg_biased_controller`
- **Tripod Gait**: Pattern con 3 patas en contacto simultáneo
- **MuJoCo Physics**: Motor de física usado por FlyGym

---

**Diagnóstico completado por**: Claude Code
**Fecha**: 2026-03-12
**Branch**: claude/analyze-code-and-documentation
