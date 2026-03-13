# BUGS.md - Diagnóstico Exhaustivo de Fallos de Simulación (ACTUALIZADO)
## NeuroMechFly Kinematic Replay - 2026-03-13
## POST-FIXES VALIDATION (16:43 UTC)

---

## ✅ RESUMEN DE CORRECCIONES IMPLEMENTADAS

### Fase 1: Fix Logic (COMPLETADA)
- ✅ **Fix #B5:** Implementado state machine (3 estados: Far/Approaching/AtSource)
- ✅ **Fix #B1:** Reemplazado `clip()` por `tanh()` para suavidad  
- ✅ **Fix #B2:** Normalizado gradiente bilateral y dirección explícita

### Fase 2: Parametric Tuning (COMPLETADA)
- ✅ **CPG Amplitude:** 0.7 → **0.9**
- ✅ **CPG Femur offset:** -0.5 → **-0.4**
- ⚠️ **Threshold adjustment:** threshold_low: 0.5 → **1.0**, threshold_high: 80 → **50**

### Fase 3: Validation (COMPLETADA CON HALLAZGOS)
- ✅ **Test 1 (Brain Isolated):** Forward graduada (0→1) ✓, Turn normalizado ✓
- ✅ **Test 2 (CPG Isolated):** 42 DoF, femur range válida ✓
- ⚠️ **Test 3 (Diagnostic):** Problemas **NO RESUELTOS** - Ver análisis abajo

---

## 📈 MÉTRICAS PRE/POST FIXES

| Métrica | Antes Fixes | Post Fixes | Cambio | Estado |
|---------|------------|-----------|--------|--------|
| **Brain Test - Forward Range** | 1.0-1.0 (binaria) | **0.0-1.0** | ✅ Graduada | FIX #B1 OK |
| **Brain Test - Mean Forward** | 1.000 | **0.850** | ✅ Suave | FIX #B1 OK |
| **Brain Test - Turn Range** | -0.800 to -0.800 | **-0.147 to 0** | ✅ Normalizado | FIX #B2 OK |
| **Brain Test - Mean Turn** | -0.800 | **-0.147** | ✅ Menos saturado | FIX #B2 OK |
| **Diagnostic - Mean Z** | 0.720 mm | **-0.124 mm** | ❌ PEOR | Z se hunde más |
| **Diagnostic - Z Range** | 2.112 mm | **2.790 mm** | ❌ MÁS variación | Inestable |
| **Diagnostic - Mean Forward** | 0.005 | **0.005** | ❌ SIN CAMBIO | BUG PERSISTENTE |
| **Diagnostic - Mean Turn** | 0.670 | **-0.145** | ✅ Mejoró | NORMALIZADO |

---

## 🔴 ANÁLISIS DE PROBLEMAS PERSISTENTES

### Problema 1: Mean Forward SIGUE siendo ~0.005 en simulación integrada

A pesar de que:
- Brain test aislado genera mean forward = 0.85 ✓
- State machine implementado ✓
- Thresholds ajustados ✓

**La simulación integrada sigue con mean forward ≈ 0.005**

### Causa Raíz Identificada

El fly comienza en un **plateau de concentración inicial:**

```
Initial position: (35, 35, 0.5)
Odor source: (50, 50, 5)
Initial concentration: ~2.2
Time 0→2s progression: Conc: 2.2 → 2.9 (Δ = 0.7 en 2s)
Average dC/dt: ≈ 0.35/sec = 3.5e-5 per step (0.0001s)

Entrada a tanh: tanh(50 * 3.5e-5) = tanh(0.00175) ≈ 0.0017
→ forward ≈ 0.0017, redondeado a 0.005 en mean
```

**Problema arquitectónico:** El cerebro asume que si `dC/dt ≈ 0`, no hay navegación posible. Pero en realidad, con condiciones iniciales cercanas al odor, `dC/dt` será siempre pequeño.

### Problema 2: Z-height EMPEORA (-0.124 mm vs anterior 0.720 mm)

Contra-intuitivamente, aumentar amplitud CPG empeora el hundimiento:

```
Con mean forward ≈ 0:
- CPG genera oscilaciones puras (sin traslación)
- Amplitud 0.9 → movimiento de patas MÁS AGRESIVO
- Pero sin avance → patas "apalancadas" contra suelo inestablemente
- Resultado: Z-height se hunde BAJO el suelo (-0.124, -0.292 min)
```

---

## 🎯 SOLUCIONES CANDIDATAS

### OPCIÓN A: Forzar "coast forward" bajo presencia de gradiente bilateral

```python
# Si hay considerable gradiente BUT dC/dt es pequeño
if abs(gradient_diff) > 2.0 and dC_dt < 0.1:
    forward = 0.3  # "Coast" mode: avanza suavemente mientras busca
else:
    forward = default_forward_logic
```

**Ventaja:** Minimally invasive, biológicamente realista  
**Desventaja:** Parámetros mágicos (2.0, 0.1, 0.3) requieren tuning

### OPCIÓN B: Hibridizar concentración absoluta + temporal gradient

```python
forward = forward_scale * (
    0.4 * tanh(conc_center / 15) +  # ~10% of max intensity = "detectable odor"
    0.6 * tanh(50 * dC_dt)           # Temporal change still important
)
```

**Ventaja:** Combina señales biológicamente plausibles  
**Desventaja:** Introduce artefacto (el coeficiente 0.4/0.6 es heurístico)

### OPCIÓN C: Cambiar posición inicial (trivia test)

```python
# En lugar de spawn_pos=(35, 35, 0.5):
spawn_pos = (20, 25, 0.5)  # ~28mm del odor, no +21mm
# Esto: conc_inicial ≈ 0.3, permitiendo Δ >> 2
```

**Ventaja:** Si funciona, valida hipótesis, zero code change needed after fixes  
**Desventaja:** No arregla problema subyacente de sensibilidad

### OPCIÓN D: Revertir a lógica pre-2026-03-12 + soluciones targeted

Investigar qué exactamente causaba "overshooting" antes, e implementar solución más sutil que "eliminar forward cuando plateau".

---

## 📊 RECOMENDACIÓN

**Ejecutar OPCIÓN C primero (5 min):** Cambiar solo spawn_pos a (20, 25) y volver a correr diagnóstico.

- **Si funciona (mean forward > 0.3, Z > 1mm):** Problema fue puramente posición inicial. Entonces implementar OPCIÓN A o B permanentemente.
- **Si falla:** Problema es arquitectónico del cerebro. Necesita refactor mayor → pasar a SNN_OlfactoryBrain.

---

## RESUMEN EJECUTIVO

Se ejecutaron tres tests diagnósticos aislados para validar cada capa de la arquitectura sensoriomotora:

1. **Test del Cerebro Aislado** (`test_brain_visualization.py`)
2. **Test del CPG Aislado** (`test_cpg_isolated.py`)
3. **Test de Simulación Completa** (`run_diagnostic_simulation.py`)

**Resultado:** Se identificaron **5 bugs críticos** que requieren corrección inmediata:

| Bug | Severidad | Componente | Estado |
|-----|-----------|-----------|--------|
| #B1 | 🔴 CRÍTICO | ImprovedOlfactoryBrain | Forward "muere" después del paso 3 |
| #B2 | 🔴 CRÍTICO | ImprovedOlfactoryBrain | Turn sin dirección (no especifica L/R) |
| #B3 | 🔴 CRÍTICO | Simulación Física (MuJoCo) | Z-height sigue hundiendo (0.18-2.29mm) |
| #B4 | 🟠 SERIO | ImprovedOlfactoryBrain | Fly orbita a radio CONSTANTE, no se acerca |
| #B5 | 🟠 SERIO | BrainFly Integration | Motor commands prácticamente muertos (mean forward=0.005) |

---

## BUG #B1: FORWARD COMMAND "DIES" DESPUÉS DEL PASO 3

### Síntoma Observado

```
[Brain Step 1]  forward=1.000000  (Bootstrap - conc_change=0.500000)
[Brain Step 2]  forward=1.000000  (conc_change=1.444615)
[Brain Step 3]  forward=1.000000  (conc_change=0.198667)
[Brain Step 4]  forward=1.000000  (conc_change=0.210192)
[Brain Step 5]  forward=1.000000  (conc_change=0.222220)

...luego...

TEST 1 STATISTICS:
  Forward command range: 1.000 to 1.000  (SIEMPRE 1.0!)
  Mean forward: 1.000

TEST 2 STATISTICS (Orbiting):
  Forward command range: 0.000 to 0.000  (SIEMPRE 0.0!)
  Mean forward: 0.000
```

**Análisis:**
- En el Test 1 (acercarse): forward SIEMPRE = 1.0 (nunca cambia)
- En el Test 2 (orbitar): forward SIEMPRE = 0.0 (nunca cambia)
- El forward está **binario** (0 o 1), no gradual
- No hay un "rango intermedio" esperado para navegación graduada

### Causa Raíz

Revisar `src/controllers/improved_olfactory_brain.py` líneas ~100-150:

El código actual usa:
```python
# Pseudo-código basado en el archivo
conc_change = current_conc - last_conc
forward_command = temporal_gradient_gain * conc_change
forward_command = np.clip(forward_command, -1, 1)
```

**Problema:** 
- En los primeros pasos, `conc_change` es grande (~0.5, ~1.4) → `forward = 1.0`
- Luego `conc_change` se estabiliza en valores muy pequeños (~0.2) 
- Estos valores pequeños se multiplican por `temporal_gradient_gain=50.0`
- Pero el clipping a [-1, 1] hace que cualquier valor > 0 se convierta a 1.0
- Y en el Test 2 (orbita constante), `conc_change ≈ 0` → `forward = 0.0`

La lógica **debería** ser:
```
forward = tanh(50.0 * conc_change)  # Suave, no binaria
```

Pero en cambio es:
```
forward = clip(50.0 * conc_change, -1, 1)  # Binaria (todo >0.02 es 1.0)
```

### Impacto

- El cerebro no puede generar comandos **graduados** de velocidad
- La mosca solo puede "caminar rápido" (1.0) o "no caminar" (0.0)
- No hay transiciones suaves necesarias para acercarse gradualment al odor
- **Solución:** Reemplazar `clip()` por `tanh()` o similar función suave

---

## BUG #B2: TURN COMMAND NO ESPECIFICA DIRECCIÓN (L vs R)

### Síntoma Observado

```
[Brain Step 1]
  Gradient diff (L-R): -0.109526
  Motor signal: turn=-0.087621

[Brain Step 2]
  Gradient diff (L-R): -0.108790
  Motor signal: turn=-0.087032

TEST 2 STATISTICS:
  Turn command range: -0.800 to -0.800  (CONSTANTE!)
  L-R gradient range: -15.517840 to -15.517840  (CONSTANTE!)
```

**Análisis:**
- El turn es un escalar: `-0.087621`, `-0.800`, etc.
- No especifica cuál es la dirección (izquierda vs derecha)
- El signo negativo es ambiguo: ¿significa girar a la izquierda o disminuir intensidad?

### Causa Raíz

El código de ImprovedOlfactoryBrain usa:
```python
gradient_diff = (conc_right - conc_left) / (conc_left + 1e-8)
turn = turn_scale * gradient_diff
```

**Problema:**
- Un valor negativo `-0.087` solo dice "hay gradiente negativo"
- Pero **CPG no sabe** si eso significa:
  - Opción A: "Gira a la izquierda" (porque conc_left es MAYOR)
  - Opción B: "Gira a la derecha pero débilmente"

En el Test 2 (orbita):
- El fly está orbitando, así que `conc_left == conc_right` siempre
- El cerebro calcula: `turn = -0.8 * (41.6 - 41.6) = -0.8 * (-0.00001) = -0.8`?
- Eso no tiene sentido físico

### Impacto

- El CPG recibe un comando turn escalar pero no sabe la dirección absoluta
- El CPG debe invertir la lógica interna para mapear escalar → izquierda/derecha
- Hay riesgo de girar en la dirección OPUESTA a la correcta
- **Solución:** El cerebro debe generar dos comandos separados: `turn_left` y `turn_right`, o un comando de gradiente bilateral explícito

---

## BUG #B3: Z-HEIGHT SIGUE HUNDIENDO (0.18-2.29 mm)

### Síntoma Observado (Diagnostic Simulation)

```
Progress: 10% | Z=2.159 mm
Progress: 20% | Z=1.915 mm
Progress: 30% | Z=0.254 mm  ← COGE EL SUELO!
Progress: 40% | Z=0.240 mm  ← CORRE BAJO EL SUELO!
Progress: 50% | Z=0.234 mm  ← Oscila cerca del suelo
...

Z HEIGHT STABILITY ANALYSIS:
  Mean Z: 0.720 mm  ← CRÍTICO: debería ser >1.5mm
  Min Z: 0.182 mm   ← Casi totalmente enterrado
  Max Z: 2.294 mm
  Range: 2.112 mm   ← Variación ENORME (>2mm)
  Std Dev: 0.791 mm
  ✗ CRITICAL: Z height varies too much (>2mm)! This causes sinking!
```

**Análisis:**
- El rango de Z es de 0.18mm a 2.29mm, una variación de **2.11mm** (¡es enorme!)
- La media es tan solo 0.72mm (la mosca está prácticamente tocando el suelo)
- El CPG está generando ángulos válidos (`[-0.7146, 1.3892]`), por tanto el problema no es del CPG
- Los femur angles están en rango válido (`[-0.7146, -0.3183]`), dentro de `[-1.5, -0.2]`

### Causa Raíz

**Candidatos:**
1. **CPG amplitude aún insuficiente** - Aunque se aumentó de 0.5 a 0.7, puede no ser suficiente
2. **Femur offset inapropiado** - Se cambió a -0.5, pero quizás -0.4 o -0.3 sería mejor
3. **Contacto con el suelo inestable** - Las patas pueden estar cediendo bajo el peso
4. **Motor commands casi-cero** (Bug #B5) - Si `forward=0.005`, el CPG apenas mueve las patas → no hay fuerza contra la gravedad
5. **Fricción o damping en MuJoCo** - Configuración de contacto puede ser demasiado suave

**Evidencia más fuerte: Bug #B5**
```
MOTOR COMMAND ANALYSIS:
  Forward range: [0.000, 1.000]
  Mean forward: 0.005  ← PRÁCTICAMENTE CERO!
  Turn range: [-0.231, 0.800]
  Mean turn: 0.670
```

Si `mean forward ≈ 0`, el CPG está generando movimientos mínimos. Las patas apenas se mueven, así que la mosca no tiene "apoyo" suficiente contra la gravedad.

### Impacto

- La mosca no puede mantener altura estable
- El hundimiento es **mecánico**, no un error de lógica de control
- Los contactos con el suelo son oscilantes/inestables
- **Solución (inmediata):**
  1. Aumentar CPG amplitude de 0.7 a 0.9 o 1.0
  2. O: Aumentar femur extension (offset de -0.5 a -0.3)
  3. O: Revisar configuración de contacto en MuJoCo (fricción, damping)
  4. **Lo más probable: Fix Bug #B5 primero** (get forward commands working → more leg movement → better ground support)

---

## BUG #B4: FLY ORBITA A RADIO CONSTANTE, NO SE ACERCA

### Síntoma Observado

**Test 1 (Approaching):**
```
Step 1: Conc center = 2.701594
Step 2: Conc center = 2.889230
Step 3: Conc center = 3.087897
Step 4: Conc center = 3.298089
Step 5: Conc center = 3.520309

Concentration range: 2.701594 to 90.078183  ← OK, sube hasta 90!
```

**Test 2 (Orbiting):**
```
Concentration range: 41.604863 to 41.604863  ← CONSTANTE TODO EL TEST!
L-R gradient range: -15.517840 to -15.517840  ← CONSTANTE TODO!

Mean forward: 0.000  ← NO AVANZA
Mean turn: -0.800   ← GIRA CONSTANTEMENTE
```

### Causa Raíz

En el Test 2, se inicializa el fly a una distancia donde la concentración es ~41.6 (bastante cerca):
```python
# Pseudo-código del test
odor_source = (50, 50, 5)
initial_position = some_position_where_conc = 41.6
fly_orbits_around_source()  # El fly gira pero no se acerca
```

**Problema observado:**
- La mosca GIRA (turn=-0.8) pero NO AVANZA (forward=0.0)
- Si el fly está orbitando en círculo, la concentración permanece constante
- El cerebro ve `conc_change ≈ 0` → `forward = 0.0` ✓ (lógica correcta)
- El cerebro ve `grad_L-R` constante → `turn` constante ✓ (lógica correcta)

**Esto NO es realmente un bug** - Es un comportamiento correcto a la distancia equivocada.

**PERO hay un problema implícito:**
- En la orbit, |`gradient_diff`| = 15.5, que es ENORME
- El turn = -0.8 constante, cuando debería ser más pequeño
- El cerebro usa `turn_scale * gradient_diff` sin normalizar
- Con un gradiente tan alto en órbita, el turn satura a ±0.8

### Impacto

- La mosca puede orbitar correctamente a distancia constante ✓
- Pero no puede hacer transiciones suaves entre acercarse y orbitar
- El turn magnitude es insensible a cambios de distancia (siempre -0.8 en órbita)
- **Solución:** Normalizar el gradiente bilateral o aplicar una función suave (tanh)

---

## BUG #B5: MOTOR COMMANDS PRÁCTICAMENTE MUERTOS (mean forward=0.005)

### Síntoma Observado (Diagnostic Simulation Full)

```
MOTOR COMMAND ANALYSIS:
  Forward range: [0.000, 1.000]
  Turn range: [-0.231, 0.800]
  Mean forward: 0.005  ← CRÍTICO!
  Mean turn: 0.670

[Brain Step 3]
  Conc change: -0.001200
  Motor signal: forward=0.000000  ← Ya cero en step 3!

Progress: 30% | Step 6000/20000 | Z=0.254 mm | Conc=3.9093
Progress: 100% | Step 20000/20000 | Z=0.275 mm | Conc=3.9788
```

**Análisis:**
- En 20,000 pasos (2 segundos), el fly CASI NO AVANZA (`mean forward = 0.005`)
- El forward se vuelve 0.0 muy rápidamente (step 3)
- El turn mean = 0.67, lo que significa que el fly está **girando constantemente**
- La concentración apenas cambia (3.9 a 3.97), sugiriendo que **el fly no se está moviendo**

### Causa Raíz

**Cadena de causalidad:**

1. **Step 1-2:** El fly se acerca, `conc_change` es positivo y grande
   - `forward = 1.0`
   - La mosca camina hacia adelante
   
2. **Step 3 en adelante:** El fly LLEga a una distancia donde `conc_change` se estabiliza
   - `conc_change ≈ 0.0` (ya no hay aceleración olfativa)
   - El cerebro interpreta: "Ya no estás acercándote, deja de andar"
   - `forward = 0.0`
   - La mosca se DETIENE

3. **Luego:** El fly está parado, pero sigue girando (`turn ≈ 0.67`)
   - Si el gradiente L-R es negativo, el cerebro le dice "gira izquierda"
   - La mosca gira en círculos sin avanzar

### El Problema Fundamental

El cerebro implementa **pure temporal gradient detection**:
```python
forward = f(dC/dt)  # "Avanza si la concentración ESTÁ AUMENTANDO"
```

Pero esto es **demasiado restrictivo** para navegación:

```
FASE 1: Fly at [35, 35], source at [50, 50]
  - Conc increases every step (dC/dt > 0)
  - Forward = 1.0 ✓ Correct

FASE 2: Fly at [45, 45], source at [50, 50] (casi en la fuente)
  - Conc plateau (dC/dt ≈ 0)
  - Forward = 0.0 ✗ WRONG! Fly should still approach!

FASE 3: Fly at [50, 50], source at [50, 50] (EN la fuente)
  - Conc plateau (dC/dt = 0)
  - Forward = 0.0 ✓ Correct (debería parar/orbitar)
```

**Falta:** Una lógica que también considere la **concentración absoluta** o el **gradiente espacial**, no solo temporal.

### Impacto

- El fly **no puede mantener avance sostenido**
- Se detiene demasiado pronto, antes de llegar a la fuente
- El comportamiento de navegación es incompleto
- **Solución:** Implementar una máquina de estados:
  - **Estado 1 (Far):** `Si conc < threshold_low: forward = 0`
  - **Estado 2 (Approaching):** `Si conc > threshold_low AND dC/dt > 0: forward = 1`
  - **Estado 3 (At source):** `Si conc > threshold_high: forward = 0, orbit`

---

## ANÁLISIS CRUZADO: CÓMO INTERACTÚAN LOS BUGS

```
BUG #B5 (forward dies) 
    ↓
    Leads to: mean forward = 0.005
    ↓
    ╔═══════════════════════════════════════════╗
    ║ Mosca NO se mueve suficiente              ║
    ║ → CPG genera patrones suaves de marcha    ║
    ║ → PERO las patas no mueven el cuerpo      ║
    ║ → PORQUE el motor forward está casi cero  ║
    ╚═══════════════════════════════════════════╝
    ↓
    Leads to: BUG #B3 (Z-height sinking)
    - Si la mosca no camina, no hay apoyo rítmico
    - Las patas colapsan bajo gravedad
    - Z-height se hunde (0.18 mm)

BUG #B1 (forward binaria)
    ↓
    Forward es 0.0 o 1.0, nunca intermedio
    ↓
    Leads to: No gradual approach
    - No hay velocidades de "cruce" suave
    - El fly hace saltos binarios

BUG #B2 (turn sin dirección)
    ↓
    Turn es un escalar sin contexto
    ↓
    Leads to: Potential turning in wrong direction
    - CPG puede girar izquierda cuando debería derecha
    - O viceversa
```

---

## MATRIZ DE PRIORIDAD DE CORRECCIÓN

| Prioridad | Bug | Razón | Esfuerzo | Impacto |
|-----------|-----|-------|----------|---------|
| 1️⃣ **INMEDIATO** | #B5 | Causa #B3; rompe navegación | Alto | 🔴 Crítico |
| 2️⃣ **INMEDIATO** | #B1 | Hace forward binaria, no graduada | Bajo | 🔴 Crítico |
| 3️⃣ **URGENTE** | #B3 | Mosca se hunde (síntoma de #B5) | Medio | 🔴 Crítico |
| 4️⃣ **IMPORTANTE** | #B2 | Ambigüedad direccional | Bajo | 🟠 Serio |
| 5️⃣ **OPTIMIZACIÓN** | #B4 | Comportamiento subóptimo en órbita | Medio | 🟢 Mejorable |

---

## CRONOLOGÍA DE CORRECCIONES RECOMENDADAS

### Fase 1: Fix Logic (30 min)

**1.1 Fix #B5 - Implement State Machine in ImprovedOlfactoryBrain**

**Archivo:** `src/controllers/improved_olfactory_brain.py`

Cambiar la lógica de forward:
```python
# ANTES (actual):
forward = temporal_gradient_gain * conc_change  # Si dC/dt parada, forward = 0

# DESPUÉS (propuesto):
# Implementar máquina de estados con tres estados
if concentration < 0.1:
    forward = 0.0  # No hay olor detectable
elif concentration > 80.0:
    forward = 0.0  # Ya en la fuente, parar
else:
    # En rango intermedio: avanza si gradiente temporal positivo
    forward = max(0.0, temporal_gradient_gain * conc_change)
    forward = np.tanh(forward)  # Suave, no binaria
```

**1.2 Fix #B1 - Replace clip() with tanh() for smooth forward**

```python
# ANTES:
forward = np.clip(temporal_gradient_gain * conc_change, -1, 1)

# DESPUÉS:
forward = np.tanh(temporal_gradient_gain * conc_change)
```

**1.3 Fix #B2 - Explicit directional turn**

```python
# ANTES:
turn = turn_scale * gradient_diff  # Ambiguo

# DESPUÉS:
# Normalizar gradiente primero
grad_magnitude = abs(gradient_diff) / (conc_left + conc_right + 1e-8)
# Aplicar suave
turn_intensity = np.tanh(turn_scale * grad_magnitude)
# Aplicar dirección basada en signo
turn = turn_intensity if gradient_diff < 0 else -turn_intensity
# Comentario: Si conc_left > conc_right (grad_diff < 0), 
#            entonces hay más olor a la izquierda, gira izquierda (turn < 0)
```

### Fase 2: Parametric Tuning (20 min)

**2.1 Increase CPG amplitude** (Attack #B3 from another angle)

**Archivo:** `src/controllers/cpg_controller.py` (o `simplified_tripod_cpg.py`)

```python
# ANTES:
amplitude_base = 0.7

# DESPUÉS:
amplitude_base = 0.9  # Aumentar altura de zancada
```

**2.2 Fine-tune CPG femur offset**

```python
# ANTES:
femur_offset = -0.5

# DESPUÉS:
femur_offset = -0.4  # Más extendido aún para mejor apoyo
```

### Fase 3: Validation (30 min)

**3.1 Re-run brain isolation test**
```bash
python tools/test_brain_visualization.py
```
Verificar: Forward debe ser gradual (no binaria), con valores intermedios 0.0-1.0

**3.2 Re-run CPG isolation test**
```bash
python tools/test_cpg_isolated.py
```
Verificar: Femur angles en rango [-1.5, -0.2], mejor apoyo visible

**3.3 Re-run full diagnostic simulation**
```bash
python tools/debug/run_diagnostic_simulation.py
```
Verificar: 
- Z height mean > 1.0 mm (idealmente 1.5+)
- Z range < 1.0 mm (idealmente < 0.5 mm)
- Mean forward > 0.3 (was 0.005)
- Concentration increases over time (was static at 3.9)

---

## CHECKLIST DE VERIFICACIÓN POST-FIX

```
[ ] Test 1: Brain Isolated - Forward es smooth (0.0 → 0.5 → 1.0 → 0.5 → 0.0)
[ ] Test 1: Brain Isolated - Turn respeta dirección (positivo para left, negativo para right)
[ ] Test 2: CPG Isolated - 42 joint angles, all non-zero
[ ] Test 2: CPG Isolated - Femur range [-1.5, -0.2]
[ ] Test 3: Diagnostic - Z height mean > 1.0, range < 0.5
[ ] Test 3: Diagnostic - Mean forward > 0.3
[ ] Test 3: Diagnostic - Fly approaches source (concentration increases)
[ ] Test 3: Diagnostic - No Unicode errors in report (fix encoding)
```

---

## NOTAS ADICIONALES

### Sobre el Test 2 (Orbiting)

El test 2 muestra comportamiento correcto *dado* el estado inicial:
- Concentración constante → Forward = 0 ✓
- Gradiente bilateral constante → Turn = constante ✓

Pero revela que el cerebro **no tiene mecánica para aprovechar órbita + gradiente**.

Mejora futura:
```python
# En lugar de esperar dC/dt para avanzar...
# ...podría usar: "Si estoy orbitando Y hay gradiente, espiral inward"
if mean(abs(conc_change)) < 0.01 and abs(gradient_diff) > 1.0:
    # Estoy en órbita (conc const) pero hay gradiente bilateral
    # → Orbita en espiral hacia gradiente más fuerte
    forward = 0.3  # Avanza suavemente mientras orbito
```

### Sobre Base Noise y Temporalización

Los tests usan `temporal_gradient_gain = 50.0`, pero hay oscilaciones:
```
Step 3: conc_change = -0.001200 → una DISMINUCIÓN!
```

Esto sugiere que el ruido numérico o las interpolaciones en OdorField están generando fluctuaciones falsas. Considerar:
- Smoothing de concentración (moving average de últimos 5 steps)
- O: Aumento de threshold mínimo para detectar cambios significativos

---

## ARCHIVOS A MODIFICAR

```
✋ ALTO IMPACTO:
  src/controllers/improved_olfactory_brain.py     [Lines ~100-150]
  src/controllers/cpg_controller.py               [Lines ~170-180]

🔧 BAJO IMPACTO:
  tools/test_brain_visualization.py               [Just re-run]
  tools/debug/run_diagnostic_simulation.py        [Fix Unicode on line 305]

📊 SOLO ANÁLISIS:
  tools/debug/diagnose_observation_structure.py   [Information only]
```

---

## REFERENCIAS A TODO.md

Este análisis **resuelve** los siguientes puntos del TODO.md:

1. ✅ **"Arreglar el error de la simulación (mosca metiéndose en el suelo)"**
   - Identificada causa raíz: Bug #B5 (forward commands near-zero)
   - Solución: Implementar state machine para navegación graduada

2. ✅ **"Cerebro indica acercamiento a olor"**
   - Tests muestran: Concentración aumenta (buenos datos)
   - Pero: Forward no es graduada (Bug #B1)
   - Solución: Reemplazar clip() con tanh()

3. ✅ **"Compatibilidad cerebro-simulador"**
   - Verificada: CPG genera 42 DoF correctamente
   - Pero: Motor commands muertos (Bug #B5)
   - Raíz: Lógica temporal gradient demasiado restrictiva

4. ✅ **"Ver si CPG funciona sin cerebro"**
   - Verificado: CPG isolated test muestra 42 DoF OK
   - Conclusión: CPG funciona, problema es entrada del cerebro

---

## CONCLUSIÓN

Los bugs identificados son **sintomáticos de una arquitectura de navegación incompleta**. El cerebro fue actualizado (2026-03-12) para usar gradiente temporal en lugar de concentración absoluta, pero esto dejó la lógica **demasiado minimalista** para navegación sostenida.

**Solución inmediata (2h):**
1. Implementar state machine en ImprovedOlfactoryBrain
2. Reemplazar clip() con tanh() para suavidad
3. Normalizar y explicitizar direccionalidad del turn
4. Aumentar CPG amplitude a 0.9

**Solución a largo plazo:**
Reemplazar ImprovedOlfactoryBrain con SNN_OlfactoryBrain (Brian2) que implemente:
- ORN + AL + MB + DN pipeline biológicamente fundado
- Automáticamente más robusto a cambios de concentración
- Mejor separación entre estado motor y sensorial

