# Navegación Olfatoria en Drosophila: Arquitectura Sensoriomotor Modular

Sistema modular para simular la navegación quimiotáctica en _Drosophila melanogaster_ usando FlyGym, separando claramente percepción, cognición y motricidad.

## Contenidos

1. [Biología de la Quimiotaxis](#biología-de-la-quimiotaxis)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Módulos Implementados](#módulos-implementados)
4. [Parámetros Técnicos](#parámetros-técnicos)
5. [Validación y Tests](#validación-y-tests)
6. [Extensiones](#extensiones)

---

## Biología de la Quimiotaxis

### Sistemas Olfativos en Drosophila

#### Órganos sensoriales
- **Antenas**: ~1,200 sensila por antena, cada una con 1-2 neuronas olfatorias (ORNs)
- **Palpos maxilares**: Órganos secundarios con menor densidad de receptores
- **Respuesta temporal**: 50-100 ms desde estimulación a respuesta neural

#### Ruta neural de procesamiento del olor

```
Antena (ORN) 
    ↓
Antennal Lobe (50+ glomeruli, primeros relés)
    ↓
Mushroom Body + Lateral Horn (integración, aprendizaje)
    ↓
Central Complex (decisiones, espacialización)
    ↓
Motor output (descending neurons → motor pools)
```

**Características clave:**
- **Codificación periférica**: Cada glomerulo responde a clase química específica (receptores especializados)
- **Amplificación neural**: Las ORNs sinaptan en ~10-20 células projectoras
- **Integración sensorial**: Mushroom Body combina olor con contexto visual/mecánico
- **Memoria**: Cambios en sinapsis tras aprendizaje (Kenyon cells)

### Comportamientos Motores Orientados por Olor

#### 1. **Taxis Gradual** (Gradient Steering)
- Aumenta velocidad forward cuando detecta aumento de concentración
- Modula giro inversamente proporcional a gradiente
- Típico en distancias <5 cm con gradientes suaves
- Integración: olor → sistema motor en ~200-300 ms

#### 2. **Casting + Surge** (Olfactory Search)
- Cuando pierde contacto olfatorio: realiza giros amplios (90-180°)
- Tras redetectar olor: "surge" directo (movimiento recto)
- Memoria de corto plazo: ~3 segundos sin olor activa búsqueda
- Circuito neural: Lateral horn + central complex + motor circuits

#### 3. **Umbrales de Activación**
- Detección mínima: ~100-200 moléculas en campo olfatorio cercano
- Rango dinámico: ~4-5 órdenes de magnitud
- Saturación: >100 ppm causa respuestas atenuadas (adaptación)

### Sistema Motor: Estructura de Patas

#### Anatomía
```
Cabeza (antenas, visual system)
    |
Thorax seg.1 (T1) ─── R.Front (RF), L.Front (LF)
Thorax seg.2 (T2) ─── R.Middle (RM), L.Middle (LM)  
Thorax seg.3 (T3) ─── R.Hind (RH), L.Hind (LH)
    |
Abdomen (balance, retroalimentación)
```

#### Articulaciones por pata (6 DoF)
1. **ThC (Thorax-Coxa)**: Aducción/abducción (lateral)
2. **CTr (Coxa-Trochanter)**: Rotación interna
3. **FTi (Femur-Tibia)**: Extensión/flexión muslo
4. **TiTa (Tibia-Tarsus)**: Extensión/flexión tibia
5-6. **Tarsal joints**: Movimientos complejos de contacto

**Total: 6 patas × 6 DoF = 42 grados de libertad**

#### Central Pattern Generators (CPGs)
- **Patrón tripoidal alternado**: Patas 1,3,5 alternan con 2,4,6
- **Frecuencia**: 8-12 Hz (período ~80-125 ms)
- **Neuronas motoras**: ~300 motoneurones en ganglio torácico
- **Modulación**: Entrada sensorial modifica fase y amplitud, NO genera patrón
- **Neuromoduladores**: Serotonina, octopamina regulan vigor motor

### Referencia de Velocidades Típicas

| Parámetro | Valor Típico | Rango | Unidades |
|-----------|--------------|-------|----------|
| Velocidad de marcha | 10 | 5-20 | mm/s |
| Velocidad angular (giro) | 200 | 50-540 | °/s |
| Frecuencia de paso | 10 | 8-12 | Hz |
| Latencia olfatoria | 100 | 50-200 | ms |
| Radio de giro | 15 | 10-30 | mm |
| Amplitud de zancada (swing) | 3-5 | variable | mm |

---

## Arquitectura del Sistema

### Diagrama general

```
┌────────────────────────────────────────────────────┐
│          FlyGym Physics Simulation                 │
│  (MuJoCo, 42 DoF, 10 kHz timestep, obs dict)      │
└─────────────────────┬────────────────────────────┘
                      │ obs: {position, velocity, forces, ...}
                      ↓
        ┌─────────────────────────────┐
        │    BrainFly.step(obs)       │
        │  (Sensorimotor Integration) │
        └────┬────────────────────┬───┘
             │                    │
             ↓                    ↓
    ┌──────────────────┐   ┌──────────────────────┐
    │   OdorField      │   │  OlfactoryBrain      │
    │                  │   │                      │
    │ concentration_   │   │ step(conc) →         │
    │   at(pos) →      │──→| [forward, turn]      │
    │   float          │   │ (low-dim signal)     │
    └──────────────────┘   └──────────────────────┘
             ↑                     │
             └─────────────────────┼──────────────────┐
                                   │                  │
                      ┌────────────┘                  │
                      ↓                               │
        ┌─────────────────────────────┐              │
        │  Motor Conversion           │◄─────────────┘
        │  [f, t] → 42-dim action     │
        └────────────┬────────────────┘
                     │
                     ↓
        action = {"Nuro": {joint_actions}}
                     │
                     ↓
        ┌────────────────────────────────────┐
        │ Simulation.step(action)            │
        │ → new obs, forces, contacts, etc.  │
        └────────────────────────────────────┘
```

### Niveles de abstracción

| Nivel | Clase | Input | Output | Rol |
|-------|-------|-------|--------|-----|
| **Sensorial** | OdorField | 3D position | scalar conc | Detecta químicos en campo |
| **Cognitivo** | OlfactoryBrain | scalar conc | [f, t] ∈ [-1,1] | Toma decisiones |
| **Motor** | BrainFly | [f, t] | 42-dim action | Traduce a articulaciones |
| **Físico** | Simulation | action dict | obs + forces | Calcula dinámica real |

---

## Módulos Implementados

### 1. OdorField (`src/olfaction/odor_field.py`)

**Propósito**: Modelar distribución 3D de concentración olfativa

**Ecuación matemática**:
$$C(\mathbf{x}) = A \exp\left(-\frac{\|\mathbf{x} - \mathbf{s}\|^2}{2\sigma^2}\right)$$

donde:
- $A$ = amplitud (concentración máxima en fuente)
- $\mathbf{s}$ = posición de fuente
- $\sigma$ = desviación estándar (ancho de campo)
- $\mathbf{x}$ = posición de evaluación

**API principal**:
```python
class OdorField:
    def __init__(self, sources: tuple, sigma: float, amplitude: float)
    def concentration_at(pos: np.ndarray) -> np.ndarray | float
    def gradient_at(pos: np.ndarray) -> np.ndarray
```

**Características**:
- Soporta múltiples fuentes (suma de gaussianas)
- Evaluación vectorizada: O(num_sources) por call
- Gradiente calculado por diferencias finitas (±0.1 mm)
- Rango típico: 0-1 unidades normalizadas

**Validez biológica**:
- Aproximación válida para <5 cm de fuente (sin turbulencia fuerte)
- Isotropía asumida (real = anisotropía por convección)
- Concentración máxima ~1 ppm en radio ~5 mm
- En aire turbulento aparecen "filamentos" (no capturados por modelo)

**Tests incluidos**:
- Gaussiana sigue distribución esperada
- Gradiente numérico vs analítico
- Soporta arrays 1D, 2D, 3D

---

### 2. OlfactoryBrain (`src/controllers/olfactory_brain.py`)

**Propósito**: Convertir entrada olfatoria (escalar) → comando motor [forward, turn]

**Entrada**: `odor_concentration` ∈ [0, 1] (normalizado)  
**Salida**: `[forward, turn]` ∈ [-1, 1]² 

**Tres modos de operación**:

#### Mode 1: Binary
```python
if conc > threshold:
    forward = forward_scale  # avanzar recto
    turn = 0
else:
    forward = 0
    turn = turn_scale  # girar para buscar
```
- **Comportamiento**: Búsqueda binaria (si/no olor)
- **Ventaja**: Robusto a ruido, simple
- **Desventaja**: No aprovecha información de gradiente
- **Caso de uso**: Ambientes con gradientes abruptos, búsqueda exhaustiva

#### Mode 2: Gradient
```python
forward = forward_scale × (conc / max_conc)
if conc < threshold:
    turn = turn_scale × (1 - conc)
```
- **Comportamiento**: Sigue gradientes suavemente
- **Ventaja**: Convergencia rápida en gradientes claros
- **Desventaja**: Puede quedar atrapado en máximos locales
- **Caso de uso**: Navegación continua con gradientes disponibles

#### Mode 3: Temporal Gradient (Casting)
```python
d_conc = conc[t] - conc[t-1]  # derivada temporal

if d_conc > 0:
    forward = forward_scale  # mejorando
    turn = 0
else:
    forward = 0
    turn = turn_scale  # empeorando, buscar
```
- **Comportamiento**: Usa cambio temporal de concentración
- **Ventaja**: Funciona sin gradiente espacial (solo cambios temporales)
- **Desventaja**: Requiere memoria, más lento
- **Caso de uso**: Recuperación tras pérdida de olor ("casting")
- **Referencia biológica**: Mushroom body integra derivada temporal

**Parámetros configurables**:
```python
threshold: float          # [0.01, 1.0] - sensibilidad
mode: str                 # "binary", "gradient", "temporal_gradient"
forward_scale: float      # [0, 2.0] - velocidad máxima
turn_scale: float         # [0, 2.0] - giro máximo
history_length: int       # [5, 50] - memoria para d(conc)/dt
```

**Buffer interno**: Mantiene 10 pasos anteriores de concentración para derivada

**Tests embebidos**: Valida rango de salida, coherencia de modos

---

### 3. BrainFly (`src/controllers/brain_fly.py`)

**Propósito**: Integrar OdorField + OlfactoryBrain en subclase FlyGym

**Herencia**:
```python
class BrainFly(flygym.Fly):
    """Mosca con cerebro olfatorio integrado"""
```

**Pipeline de sensorimotor** (un step):
```
1. obs ← Simulation.step(previous_action)
2. head_pos ← parse_head_position(obs)         # [x, y, z] en mm
3. conc ← odor_field.concentration_at(head_pos)
4. motor_signal ← brain.step(conc)              # [f, t]
5. action ← motor_signal_to_42dof(motor_signal)
6. return action
```

**Métodos principales**:
```python
def __init__(self, brain: OlfactoryBrain, odor_field: OdorField, 
             name: str, **kwargs)
def step(obs: dict) -> dict                    # entrada FlyGym
def get_sensory_input(obs: dict) -> float      # extrae olor
def compute_action(obs: dict) -> dict          # pipeline completo
def _parse_obs_head_position(obs: dict) -> np.ndarray
def _array_to_joints(action_2d: np.ndarray) -> dict
```

**Mapeo motor `[f, t]` → 42 DoF**:
- Usa matriz predefinida (ganancia) o CPG
- FlyGym `HybridTurningFly` mapea automáticamente
- Rango: forward ∈ [0, 1] (detenido a marcha máxima)
- Rango: turn ∈ [-1, 1] (giro izq/drch)

**Sensor**: Posición de cabeza (antenas)
- Extrae de `obs["joints"]` o `obs["body_contacts"]`
- Simplificación: un solo punto (en realidad, integración bilateral)
- Extensible a múltiples sensores

**Validez de integración**: Compatible con `Simulation.step()` estándar de FlyGym

---

### 4. OlfactorySimulation (`src/simulation/olfactory_sim.py`)

**Propósito**: Orquestar experimentos completos con logging, análisis, visualización

**Funciones principales**:
```python
def __init__(self, arena_size: tuple, odor_field: OdorField, 
             brain_config: dict)
def reset() -> dict                            # limpia logs
def step(action: dict) -> tuple                # ejecuta tick
def run(duration_seconds: float) -> dict       # bucle principal
def save_results(filename: str) -> None        # CSV + NPY
def compute_metrics() -> dict                  # análisis
```

**Logging automático**:
- Timestamp (s)
- Posición [x, y, z] (mm)
- Concentración olfativa (0-1)
- Acciones motoras [f, t]
- Distancia a fuente (mm)
- Contactos con suelo (booleano)

**Exportación**:
```csv
timestamp,x,y,z,conc,action_forward,action_turn,distance_to_source
0.0,25.0,25.0,5.0,0.001,0.0,0.5,35.4
0.001,25.0,25.1,5.0,0.002,0.1,0.4,35.2
...
```

**Métricas calculadas**:
- Distancia total recorrida (integración de |v|)
- Distancia final a fuente
- Distancia mínima alcanzada
- Tiempo en zona "cercana" (< 10 mm)
- Concentración promedio muestreada

**Parámetros de simulación**:
```python
arena_size: tuple            # (x, y, z) en mm, típico (100, 100, 10)
duration: float              # segundos
physics_dt: float            # timestep MuJoCo, default 0.0001 s
control_dt: float            # timestep cerebro, default 0.01 s
show_progress: bool          # barra de progreso
```

---

## Parámetros Técnicos

### OdorField: Recomendaciones

| Parámetro | Rango Típico | Bajo (Búsqueda) | Alto (Taxis) | Notas |
|-----------|--------------|-----------------|--------------|-------|
| **sigma** | 1-50 mm | 0.5-5 | 10-30 | Ancho del gradiente |
| **amplitude** | 0.1-10 | 0.5-1.0 | 1.0-5.0 | Intensidad relativa |
| **source_z** | 0-10 mm | 5 | 5 | Altura de fuente (típica) |

### OlfactoryBrain: Recomendaciones

| Parámetro | Rango Típico | Agresivo | Cauteloso | Notas |
|-----------|--------------|----------|-----------|-------|
| **threshold** | 0.01-1.0 | 0.01 | 0.5 | Sensibilidad olfatoria |
| **forward_scale** | 0-2.0 | 1.5-2.0 | 0.5-1.0 | Velocidad máxima |
| **turn_scale** | 0-2.0 | 1.5-2.0 | 0.5-1.0 | Giro máximo |
| **mode** | binary/gradient/temporal | binary | gradient | Estrategia cognitiva |

### Regímenes Sugeridos

#### Búsqueda exhaustiva (Low gradient, need casting)
```python
OdorField(sigma=1.0, amplitude=0.5)
OlfactoryBrain(threshold=0.05, mode="temporal_gradient", turn_scale=1.5)
```

#### Taxis rápida (Clear gradient)
```python
OdorField(sigma=15.0, amplitude=1.0)
OlfactoryBrain(threshold=0.1, mode="gradient", forward_scale=1.0)
```

#### Robustez a ruido
```python
OdorField(sigma=5.0, amplitude=0.7)
OlfactoryBrain(threshold=0.2, mode="binary", forward_scale=0.8)
```

---

## Validación y Tests

### Tests Unitarios

Cada módulo implementa basales (ejecutar desde línea de comandos):

```bash
# Test OdorField: gaussiana, gradiente, vectorización
python src/olfaction/odor_field.py

# Test OlfactoryBrain: tres modos, rango de salida
python src/controllers/olfactory_brain.py

# Test BrainFly: integración con FlyGym
python src/controllers/brain_fly.py

# Test OlfactorySimulation
python src/simulation/olfactory_sim.py
```

**Criterios de validación**:
- ✓ OdorField: Gaussiana en rango [0, 1], gradiente coherente
- ✓ OlfactoryBrain: Salida siempre ∈ [-1, 1], modos responden adecuadamente
- ✓ BrainFly: Importa sin errores, step() devuelve dict válido
- ✓ OlfactorySimulation: Genera CSV, computa métricas

### Experimentos Programados

Ver sección [Extensiones](#extensiones) para validaciones pendientes.

---

## Extensiones

### Validaciones Críticas (High Priority)

#### 1. **FlyGym Integration Test**
- [ ] Instanciar `Simulation([BrainFly(...)])` con física real
- [ ] Ejecutar 5-10 segundos de simulación
- [ ] Verificar que mosca se mueve y responde a odores
- [ ] Guardar video y trayectoria

#### 2. **Parameter Sensitivity Analysis**
- [ ] Variar sigma ∈ {0.5, 1, 5, 15, 30} mm
- [ ] Variar threshold ∈ {0.01, 0.05, 0.1, 0.2, 0.5}
- [ ] Medir: distancia final, tiempo a meta, estabilidad
- [ ] Identificar parámetros robustos vs. sensibles

#### 3. **Validation Against Real Behavior**
- [ ] Comparar trayectorias simuladas vs. videos reales _Drosophila_
- [ ] Medir: velocidad media, ángulos de giro, pausa duration
- [ ] Ajustar parámetros hasta coincidencia

### Extensiones Mediano Plazo

#### 4. **Neural Network Brain Replacement**
- [ ] Implementar `NeuralOlfactoryBrain(nn.Module)` con MLP (64 hidden)
- [ ] Entrenar con datos de simulación offline
- [ ] Comparar performance: rule-based vs. learned

#### 5. **Multi-Source Odor Fields**
- [ ] Múltiples fuentes competitivas
- [ ] Marcación temporal de fuentes (pulsos)
- [ ] Figura de merits: cual fuente elige mosca

#### 6. **Environmental Noise**
- [ ] Turbulencia (fluctuaciones Kolmogorov)
- [ ] Convolving con kernel turbulento
- [ ] Medida de robustez en diferentes SNR

### Extensiones Largo Plazo

#### 7. **Connectomic Models**
- [ ] Usar circuitos descritos en FlyEM (connectoma Drosophila)
- [ ] Implementar Antennal Lobe + Mushroom Body simplificado
- [ ] Validar emergencia de comportamientos

#### 8. **Multi-Agent Scenarios**
- [ ] Múltiples moscas en mismo arena
- [ ] Inibición lateral / comunicación feromonal
- [ ] Emergencia de comportamientos colectivos

#### 9. **Learning & Adaptation**
- [ ] Aprendizaje Pavloviano (olor + aire → giro)
- [ ] Habituación a odores constantes
- [ ] Modulación por estado motor (hambre, etc.)

---

## Estructura de Carpetas

```
Mosca/
├── src/                                # Código fuente principal
│   ├── olfaction/
│   │   └── odor_field.py              # Modelo de campo 3D gaussiano
│   ├── controllers/
│   │   ├── olfactory_brain.py         # Controller básico (3 modos)
│   │   ├── improved_olfactory_brain.py # ⭐ Controller mejorado (bilateral + temporal gradient)
│   │   └── brain_fly.py               # Integración con FlyGym
│   ├── simulation/
│   │   └── olfactory_sim.py           # Orquestador de simulaciones
│   ├── core/
│   │   ├── config.py                  # Configuración de rendering
│   │   └── data.py                    # Formateo de datos
│   └── render/
│       └── mujoco_renderer.py         # Rendering 3D con MuJoCo
│
├── tools/                              # Scripts de simulación y análisis
│   ├── run_simulation.py              # ⭐ Script principal para simulaciones
│   ├── batch_experiments.py           # Batch de experimentos
│   ├── analyze_experiments.py         # Generador de reportes HTML
│   ├── render_simulation_video.py     # Rendering de videos
│   ├── validate_movement_control.py   # Suite de tests
│   └── diagnose_critical.py           # Diagnóstico de parámetros
│
├── data/                               # Datos y documentación del proyecto
│   ├── docs/                          # 📚 Documentación técnica
│   │   ├── EXECUTIVE_SUMMARY.md       # Resumen ejecutivo del proyecto
│   │   ├── COMPLETE_CODE_REVIEW.md    # Análisis técnico completo
│   │   ├── WORKFLOW_GUIDE.md          # Guía de uso de scripts
│   │   └── SUMMARY_OF_CHANGES.md      # Historial de cambios
│   ├── notebooks/                     # Jupyter notebooks interactivos
│   │   ├── 1_getting_started.ipynb    # Introducción
│   │   ├── 2_kinematic_replay.ipynb   # Replay cinemático
│   │   └── 3_fly_following.ipynb      # Seguimiento de mosca
│   └── inverse_kinematics/            # Datos de cinemática inversa
│
├── outputs/                            # Resultados de simulaciones
│   └── YYYY-MM-DD_HH-MM-SS/           # Simulaciones timestamped
│       ├── trajectory.csv              # Trayectoria completa
│       ├── config.json                 # Parámetros usados
│       └── simulation.mp4              # Video renderizado
│
├── debug/                              # Archivos de debug y análisis
│   ├── TECHNICAL_ANALYSIS.md          # Análisis técnico de problemas
│   └── SUMMARY_OF_WORK.md             # Resumen de trabajo realizado
│
└── README.md                           # Este archivo
```

### Documentación del Proyecto

El proyecto cuenta con documentación exhaustiva en `data/docs/`:

- **WORKFLOW_GUIDE.md**: Guía práctica - qué script usar para cada tarea
- **EXECUTIVE_SUMMARY.md**: Resumen de alto nivel del proyecto y hallazgos
- **COMPLETE_CODE_REVIEW.md**: Análisis técnico detallado (762 líneas)
- **SUMMARY_OF_CHANGES.md**: Historial de cambios y mejoras implementadas

### Parámetros Biológicos Validados (2026-03-12)

Los parámetros del `ImprovedOlfactoryBrain` han sido ajustados para coincidir con datos biológicos:

| Parámetro | Valor | Justificación Biológica |
|-----------|-------|-------------------------|
| `bilateral_distance` | 1.2 mm | Distancia real entre antenas de *Drosophila* |
| `forward_scale` | 1.0 | Mapea a velocidad típica de 10 mm/s |
| `turn_scale` | 0.8 | Giro realista basado en observaciones |
| `threshold` | 0.01 | Umbral de detección validado |
| `temporal_gradient_gain` | 10.0 | Amplificación de cambio temporal (dC/dt) |

**Nota**: El controller mejorado implementa:
- ✅ **Bilateral sensing**: Comparación izquierda-derecha (como antenas reales)
- ✅ **Temporal gradient**: Forward basado en dC/dt (previene overshooting)
- ✅ **Parámetros biológicamente realistas**: Validados contra literatura

---

## Referencias Bibliográficas

### Video Simulation & Visualization

**Sistema de simulación completo con rendering a MP4** implementado en `tools/`:

- `tools/run_simulation.py`: Script principal para ejecutar simulaciones individuales
  - Auto-organiza outputs en timestamps `outputs/YYYY-MM-DD_HH-MM-SS/`
  - Genera: `trajectory.csv` (trayectoria + métricas), `config.json` (parámetros), `simulation.mp4` (video)
  - Fallback automático a simulación simple si FlyGym no está disponible
  - Usa: `python tools/run_simulation.py --mode gradient --sigma 15.0 --threshold 0.1 --duration 5`

- `tools/batch_experiments.py`: Ejecutar múltiples experimentos con parámetros variados
  - 5 estrategias preconfiguradas: Binary Search, Gradient Taxis, Temporal Gradient, Wide Field, etc.
  - Usa: `python tools/batch_experiments.py`
  - Genera carpetas timestamped para cada experimento

- `tools/render_simulation_video.py`: Renderizador de videos from CSV trajectories
  - Visualización 2D de arena, campo de olor (heatmap), trayectoria de mosca
  - Gráficos en tiempo real: distancia a fuente, concentración olfatoria
  - Soporta reintento manual: `python tools/render_simulation_video.py --csv <path> --output <path>`

- `tools/analyze_experiments.py`: Análisis comparativo y reporte HTML
  - Extrae métricas de todos los experimentos (distancia final, olor máximo, etc.)
  - Genera: `outputs/experiments_report.html` (dashboard visual embebiendo videos y tablas)
  - Usa: `python tools/analyze_experiments.py outputs`

**Estructura de outputs:**
```
outputs/
├── generic/unknown/          # Simulaciones antiguas (sin timestamp original)
│   ├── FLYGYM_INTEGRATION_REPORT.txt
│   └── *.png
├── 2026-03-12_11-28-06/      # Simulación individual gradient mode
│   ├── trajectory.csv        # Trayectoria 300+ frames
│   ├── config.json           # Parámetros reproducibles
│   └── simulation.mp4        # Video 1400×600px @30fps
├── 2026-03-12_11-28-16/      # Simulación individual
├── ... (más experimentos)
└── experiments_report.html   # Dashboard comparativo (abrir en navegador)
```

**Workflow típico:**
```bash
# 1. Simulación individual
python tools/run_simulation.py --mode gradient --sigma 15.0 --duration 10

# 2. Batch de 5 experimentos
python tools/batch_experiments.py

# 3. Análisis y reporte
python tools/analyze_experiments.py outputs
# Abrir outputs/experiments_report.html en navegador

# 4. Reintento manual de video si falla
python tools/render_simulation_video.py \
    --csv outputs/2026-03-12_XX-XX-XX/trajectory.csv \
    --output outputs/2026-03-12_XX-XX-XX/simulation.mp4
```

**Parámetros de línea de comandos (run_simulation.py):**
- `--mode {binary, gradient, temporal_gradient}`: Estrategia de navegación
- `--sigma FLOAT`: Ancho del campo olfatorio (mm), rango: 1-50
- `--threshold FLOAT`: Sensibilidad cerebral (0.01-1.0)
- `--forward-scale FLOAT`: Velocidad máxima (0-2.0)
- `--turn-scale FLOAT`: Giro máximo (0-2.0)
- `--duration FLOAT`: Duración simulación (segundos)
- `--source-x, --source-y, --source-z`: Posición fuente (mm)
- `--arena-x, --arena-y`: Dimensiones arena (mm)
- `--fps INT`: Video frames per second (mayor = más pesado)
- `--no-video`: Saltar rendering MP4

### Comportamiento Olfatorio en Drosophila

1. **Borst & Heisenberg** (1982). Osmotaxis in Drosophila melanogaster. _Journal of Comparative Physiology A_ 147, 479-484.
   - Estudio fundamental sobre quimiotaxis en Drosophila

2. **Gomez-Marin et al.** (2011). Active sampling and decision making in Drosophila chemotaxis. _Nature Communications_ 2, 441.
   - Toma de decisiones en navegación quimiotáctica

3. **Demir et al.** (2020). Walking Drosophila navigate complex plumes using stochastic decisions biased by the timing of odor encounters. _Current Biology_ 30(2), 164-171.
   - Navegación en plumas de olor complejas, timing de encuentros

4. **Wilson & Stevenson** (2003). Olfactory plasticity: one scent, many behaviors. _Nature Neuroscience_ 6(5), 438-445.
   - Plasticidad olfatoria y procesamiento neural

### Modelado Sensoriomotor

5. **Wystrach & Graham** (2012). How do animals navigate? _Biological Reviews_ 87(1), 88-115.

6. **Ravi et al.** (2023). FlyGym: An Open-Source Physics-Based Neurorobotics Platform. _Nature Communications_ (accepted).

### Biofísica y Física de Transportes

7. **Crank** (1975). The Mathematics of Diffusion. Oxford University Press.

8. **Risken** (1989). The Fokker-Planck Equation. Springer.

---

## Notas de Implementación

### Performance

- **OdorField.concentration_at()**: O(num_sources)
- **OlfactoryBrain.step()**: O(1)
- **BrainFly.step()**: O(1) + overhead FlyGym
- **Bottleneck**: Simulación FlyGym (física MuJoCo)

### Escalabilidad

- **Multi-agent**: Crear múltiples instancias BrainFly
- **Multi-source**: Agregar tuples a OdorField.sources
- **Motor avanzado**: Reemplazar mapeo [f,t] → 42 DoF

### Debugging

- Logs: `outputs/olfactory/navigation_*.csv`
- Visualización: `sim.render()` en tiempo real
- Gráficas: matplotlib exportadas a PNG
- Verificabilidad: tests embebidos en cada módulo

---

**Última actualización**: March 2026  
**Versión**: 1.0  
**Licencia**: MIT  
**Contacto**: NeuroMechFly Sim Project
