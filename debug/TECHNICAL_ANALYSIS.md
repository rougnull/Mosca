Technical Analysis & Solutions
================================

## PROBLEMA 1: MOSCA SE ALEJA CUANDO ESTÁ CERCA AL OLOR

### Análisis del Problema
Cuando se ejecutaba la simulación olfatoria, se observó que:
1. La mosca se ACERCABA al olor correctamente
2. PERO cuando estaba muy cerca de la fuente, seguía caminando hacia adelante
3. Terminaba ALEJÁNDOSE de la fuente

### Investigación Root Cause
Se analizó el cerebro olfatorio bilateral mejorado (ImprovedOlfactoryBrain):

```python
# CÓDIGO ANTERIOR (MALO):
forward = self.forward_scale * np.clip(conc_center, 0, 1)
```

**El problema**: 
- Forward se calculaba basado en concentración ABSOLUTA
- En la fuente: conc=1.0 → forward=0.5 (MÁXIMO)
- Entonces la mosca caminaba a velocidad máxima DIRECTAMENTE SOBRE la fuente
- Y se alejaba del otro lado

**¿Por qué pasa esto?**
El control bilateral solo detecta la DIFERENCIA izquierda-derecha:
```python
gradient_difference = conc_left - conc_right
```

Cuando la mosca camina DIRECTAMENTE hacia la fuente:
- Posición: mosca siempre en línea con la fuente
- conc_left ≈ conc_right (siempre)
- gradient ≈ 0 (sin información de giro)
- turn = 0 (no gira)
- forward = conc (camina recto)
- **Resultado**: Camina recto a través de la fuente ❌

### Solución: TEMPORAL GRADIENT

Cambio de usar concentración ABSOLUTA a cambio TEMPORAL de concentración.

```python
# CÓDIGO NUEVO (CORRECTO):
if len(self._concentration_history) > 0:
    conc_change = conc_center - self._concentration_history[-1]
else:
    conc_change = 0.0

forward = self.forward_scale * np.clip(conc_change * 10, 0, 1)
```

**¿Cómo funciona?**
- `conc_change = dC/dt` (cambio temporal)
- Cuando la mosca SE ACERCA: dC/dt > 0 → forward aumenta ✓
- Cuando está EN la fuente: dC/dt ≈ 0 → forward ≈ 0 ✓
- Cuando se ALEJAN: dC/dt < 0 → forward = 0 (clipped) ✓

**Comportamiento resultante:**
1. Mosca detecta olor → empieza a caminar lentamente
2. A medida que se acerca, dC/dt aumenta → forward aumenta
3. Llega cerca de fuente, dC/dt empieza a disminuir → forward disminuye
4. EN la fuente, dC/dt ≈ 0 → forward ≈ 0 → PARA
5. Si detecta aumento de olor (giro por bilateral) → gira
6. Si detecta disminución (se aleja) → forward = 0 → PARA

### Verificación

```
Test output showing velocity profile:
Position    Forward
Far (30-40): 0.145-0.236 (aumenta)
Mid (40-46): 0.236-0.220 (pico)
Close(46-48): 0.220-0.084 (disminuye)
Near (48-50): 0.084-0.012 (cae dramáticamente)
At src (50+): 0.012-0.000 (se detiene)
```

✓ PASS: Temporal gradient funciona correctamente


## PROBLEMA 2: VIDEO OUTPUT ES 2D MATPLOTLIB EN LUGAR DE 3D MUJOCO

### Investigación

Diagnóstico de disponibilidad:
- FlyGym: ✓ INSTALLED
- MuJoCo: ✓ INSTALLED
- matplotlib animation: ✓ AVAILABLE

Pero: Video sigue siendo 2D con gráficos de trayectoria XY

### Root Cause

El pipeline de `run_simulation.py`:
```python
# Lines ~270-290
render_path = Path(__file__).parent / "render_simulation_video.py"
# Carga SimulationVideoRenderer que es MATPLOTLIB (2D)
```

Archivos disponibles pero NO USADOS:
- `tools/visualization/visualize_3d_mujoco.py` (MuJoCo 3D) ← NO SE LLAMA
- `tools/render_simulation_video.py` (matplotlib 2D) ← SI SE LLAMA

### Solución

Creado nuevo script: `tools/run_mujoco_simulation.py`

**Características:**
1. Usa FlyGym para REAL physics simulation (si disponible)
2. Registra trajectory durante simulation
3. Guarda video 3D con kinemática real
4. Falls back a kinematic simulation si FlyGym falla

```python
# Estructura
try:
    # REAL FlyGym physics integration
    sim = Simulation(fly=fly, arena=arena)
    for step in range(n_steps):
        motor = brain.step(odor_field, fly_pos, heading)
        obs, _, _, _, _ = sim.step(action)
        # Record trajectory
except Exception:
    # Fallback: simple kinematic
    from tools.simple_olfactory_sim import SimpleOlfactorySim
```

### Mejoras Realizadas

1. **Updated `tools/simple_olfactory_sim.py`**
   - Ahora usa `ImprovedOlfactoryBrain` 
   - Toma posición y heading (no solo concentración)
   - Implementa bilateral sensing + temporal gradient

2. **Nuevos scripts de debug**
   - `debug/mujoco_issues/debug_mujoco_video.py` - Diagnóstico
   - `debug/test_gradient_fix.py` - Validación del arreglo


## ARQUITECTURA RESULTANTE

```
Opción 1: MuJoCo Completo (Recomendado)
  run_mujoco_simulation.py
    ↓
  FlyGym (physics)
    ↓
  ImprovedOlfactoryBrain (temporal gradient + bilateral)
    ↓
  Video 3D + Trajectory CSV

Opción 2: Kinematic Simplificado (Fallback)
  simple_olfactory_sim.py
    ↓
  Kinematic model (sin physics)
    ↓
  ImprovedOlfactoryBrain
    ↓
  Trajectory CSV → Matplotlib visualization
```

## CÓMO PROBAR

### Test 1: Algoritmo de Gradiente
```bash
python debug/test_gradient_fix.py
```
Esperado: "Forward velocity decreases near source" ✓

### Test 2: Simulación Cinemática
```bash
python tools/simple_olfactory_sim.py --duration 10
```
Esperado: Mosca se acerca sin overshooting

### Test 3: MuJoCo Full Stack
```bash
python tools/run_mujoco_simulation.py --duration 10
```
Esperado: Video 3D con kinemática real

## PARÁMETROS CLAVE

ImprovedOlfactoryBrain:
- `bilateral_distance=2.0` mm (distancia entre antenas simuladas)
- `forward_scale=0.5` (velocidad máxima)
- `turn_scale=1.0` (escala de giro)
- `threshold=0.0001` (umbral de activación)

Temporal Gradient Scaling:
- `conc_change * 10` = factor de amplificación

## REFERENCIAS

### Biología de Mosca Drosophila
La verdadera quimiotaxis en moscas usa:
1. **Bilateral sensing** - antenas izq/derecha detectan gradientes
2. **Temporal gradient** - cambio de concentración en el tiempo
3. **Chemotaxigene** - movimiento dirigido hacia atrayentes

Nuestro modelo implementa 1 + 2, acercándose más a biologismo.

### Paper relevante
https://www.nature.com/articles/s41586-024-07763-9
(Mencionado por user - contiene detalles de olfatoria en Drosophila)
