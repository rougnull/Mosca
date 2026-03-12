# Guía de Workflow - Mosca Olfactory Navigation

Esta guía clarifica qué scripts usar para cada tarea común.

---

## 🚀 Simulaciones

### NUEVO: Pipeline completo (Simulación → Validación → Renderizado 3D)

**Recomendado para la mayoría de casos:**

```bash
# Simulación completa: corre simulación, valida, y renderiza 3D (si exitosa)
python tools/run_simulation_complete.py \
    --duration 10 \
    --brain improved \
    --sim-type kinematic
```

**Caracte rísticas**:
- ✓ Ejecuta simulación y guarda trajectory.csv
- ✓ Valida que la mosca se movió correctamente
- ✓ Renderiza 3D SOLO si validación es exitosa
- ✓ Crea timestamped folders automáticamente
- ✓ Genera validation.json con detalles

**Genera**: `outputs/simulations/YYYY-MM-DD_HH-MM-SS/` con:
- `trajectory.csv` - Datos crudos de trayectoria
- `config.json` - Parámetros de simulación
- `validation.json` - Resultado de validación
- `fly_3d_animation.mp4` - Video 3D (si validación OK)

### Alternativa: Ejecutar componentes por separado (desarrollo)

**Para desarrollo/debugging, ejecutar cada paso independientemente:**

```bash
# Paso 1: Solo simulación (guarda datos): 
python tools/simulation/simulation_runner.py \
    --duration 10 \
    --sim-type kinematic

# Paso 2: Validar después
python tools/simulation/simulation_validator.py \
    outputs/simulations/2026-03-12_14-35-22/trajectory.csv

# Paso 3: Renderizar si validación OK
python tools/simulation/3d_renderer.py \
    outputs/simulations/2026-03-12_14-35-22/ \
    --quality high
```

### Ejecutar batch de experimentos
```bash
python tools/batch_experiments.py
```
**Genera**: Múltiples simulaciones con diferentes parámetros preconfigurados

### Simulación rápida sin física (testing)
```bash
python tools/simple_olfactory_sim.py --duration 10 --output test.csv
```
**Usa**: Cinemática simple, no requiere FlyGym, útil para prototipos

---

## 📊 Análisis

### Análisis batch (múltiples experimentos)
```bash
python tools/analyze_experiments.py outputs/
```
**Genera**: `outputs/experiments_report.html` (dashboard interactivo)

### Análisis detallado de un experimento individual
```bash
python tools/analysis/generate_improved_report.py outputs/YYYY-MM-DD_HH-MM-SS/
```
**Genera**: Análisis comprehensivo con múltiples métricas

### Análisis de sensibilidad paramétrica
```bash
python tools/analyze_parameters.py
```
**Genera**: Sweep de parámetros (sigma, threshold, etc.) con comparaciones

---

## 🎥 Visualización

### Generar video desde CSV existente
```bash
python tools/render_simulation_video.py \
    --csv outputs/YYYY-MM-DD_HH-MM-SS/trajectory.csv \
    --output outputs/YYYY-MM-DD_HH-MM-SS/simulation.mp4
```

### Visualización 3D MuJoCo
```bash
python tools/visualization/visualize_3d_mujoco.py
```
**Requiere**: FlyGym instalado

---

## 🔍 Diagnóstico

### Diagnosticar detección de olor
```bash
python tools/diagnose_critical.py
```
**Muestra**: Concentraciones en diferentes posiciones, ayuda a entender por qué ciertos parámetros fallan

### Diagnosticar comportamiento de simulación
```bash
python tools/diagnose_behavior.py outputs/YYYY-MM-DD_HH-MM-SS/
```
**Analiza**: Trayectorias, velocidades, giros

### Verificar instalación de FlyGym
```bash
python tools/diagnose_flygym.py
```

---

## ✅ Testing y Validación

### Tests unitarios de módulos
```bash
python tools/validate_movement_control.py
```
**Testa**: OdorField, OlfactoryBrain, navegación básica

### Validación visual
```bash
python tools/validate_visual.py
```
**Genera**: Visualizaciones de diagnóstico del pipeline

---

## 🧪 Ejemplos y Tutoriales

### Ejemplo mínimo funcional
```bash
python tools/example_minimal.py
```

### Ejemplo offline (sin FlyGym)
```bash
python tools/run_olfactory_example.py
```

---

## 📦 Organización de Outputs

Estructura recomendada:
```
outputs/
├── YYYY-MM-DD_HH-MM-SS/          # Simulación individual
│   ├── trajectory.csv
│   ├── config.json
│   └── simulation.mp4
│
├── Experiment - NAME/            # Batch de experimentos
│   ├── run_001/
│   ├── run_002/
│   └── summary.html
│
└── experiments_report.html       # Dashboard comparativo
```

---

## 🎯 Workflows Comunes

### Workflow 1: Exploración rápida de parámetros
```bash
# 1. Probar diferentes configuraciones
python tools/batch_experiments.py

# 2. Analizar resultados
python tools/analyze_experiments.py outputs/

# 3. Abrir HTML report en navegador
# Ver outputs/experiments_report.html
```

### Workflow 2: Simulación individual detallada
```bash
# 1. Ejecutar simulación
python tools/run_simulation.py --mode gradient --sigma 15 --duration 10

# 2. Análisis detallado
python tools/analysis/generate_improved_report.py outputs/YYYY-MM-DD_HH-MM-SS/

# 3. Si necesitas regenerar video
python tools/render_simulation_video.py --csv outputs/.../trajectory.csv
```

### Workflow 3: Debug de parámetros que no funcionan
```bash
# 1. Diagnosticar campo de olor
python tools/diagnose_critical.py

# 2. Probar con simulación simple
python tools/simple_olfactory_sim.py --sigma 5.0 --threshold 0.01

# 3. Si funciona, escalar a física completa
python tools/run_simulation.py --sigma 5.0 --threshold 0.01
```

---

## 🔧 Scripts NO Recomendados (Deprecated/Legacy)

- ❌ `tools/generate_analysis_report.py` → Usar `analyze_experiments.py`
- ⚠️ `tools/analyze_simulations.py` → Considerar `analysis/generate_improved_report.py`
- ❌ `tools/simulation/run_improved_simulation.py` → ELIMINADO (usar run_simulation.py)
- ❌ `tools/simulation/run_bilateral_simulation.py` → ELIMINADO (usar run_simulation.py)

---

## 📝 Configuración de Parámetros

### Parámetros recomendados (biológicamente realistas)

**Búsqueda en gradiente suave:**
```bash
--mode gradient --sigma 15.0 --threshold 0.1 --forward-scale 1.0 --turn-scale 0.8
```

**Búsqueda exhaustiva (gradiente estrecho):**
```bash
--mode temporal_gradient --sigma 5.0 --threshold 0.05 --turn-scale 1.2
```

**Taxis rápida (gradiente claro):**
```bash
--mode gradient --sigma 25.0 --threshold 0.05 --forward-scale 1.2
```

---

## 🐛 Troubleshooting

### Error: "FlyGym not available"
**Solución**: Usar `simple_olfactory_sim.py` o instalar FlyGym:
```bash
pip install flygym
```

### Video no se genera
**Solución**: Regenerar manualmente:
```bash
python tools/render_simulation_video.py --csv <path>
```

### Mosca no detecta olor
**Solución**: Diagnosticar:
```bash
python tools/diagnose_critical.py
```
Verificar que `sigma` y `amplitude` generen campo detectable en posición inicial.

---

**Última actualización**: 2026-03-12
**Para más detalles**: Ver `COMPLETE_CODE_REVIEW.md` y `README.md`
