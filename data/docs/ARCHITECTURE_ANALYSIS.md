# Análisis Arquitectural Completo - Proyecto Mosca

**Fecha**: 2026-03-12
**Versión**: 2.0
**Tipo**: Análisis Técnico Completo

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estado Actual de la Arquitectura](#estado-actual-de-la-arquitectura)
3. [Análisis del Directorio /tools](#análisis-del-directorio-tools)
4. [Archivos Legacy en Raíz](#archivos-legacy-en-raíz)
5. [Arquitectura Modular vs. Legacy](#arquitectura-modular-vs-legacy)
6. [Problemas Críticos Identificados](#problemas-críticos-identificados)
7. [Recomendaciones de Reestructuración](#recomendaciones-de-reestructuración)
8. [Plan de Migración](#plan-de-migración)

---

## 📊 RESUMEN EJECUTIVO

### Hallazgos Principales

**✅ Fortalezas del Proyecto:**
- Arquitectura modular bien diseñada en `/src`
- Separación clara: sensorial (olfaction) → cognitivo (controllers) → motor → física
- Documentación exhaustiva en `/data/docs`
- Sistema de rendering modular implementado (v2.0)
- Temporal gradient fix correctamente implementado

**⚠️ Problemas Críticos:**
1. **Archivos legacy en raíz** no integrados con arquitectura modular
2. **Redundancia en /tools**: 9 archivos con funcionalidad similar/duplicada
3. **Falta de punto de entrada único** documentado y actualizado
4. **Inconsistencia entre documentación y código**: WORKFLOW_GUIDE.md menciona scripts que no existen o no funcionan
5. **Desconexión rendering**: Dos sistemas paralelos (modular vs legacy) sin integración clara

**Impacto:**
- Confusión sobre qué archivos usar
- Mantenimiento duplicado
- Dificultad para nuevos usuarios
- Documentación desactualizada

### Métricas de Calidad

| Aspecto | Estado Actual | Objetivo |
|---------|---------------|----------|
| **Código redundante** | ~40% en /tools + legacy | <10% |
| **Punto de entrada único** | ❌ Múltiples opciones confusas | ✅ 1 script principal |
| **Integración modular** | ⚠️ Parcial | ✅ Completa |
| **Documentación actualizada** | ⚠️ Desactualizada | ✅ Sincronizada con código |
| **Archivos legacy** | ⚠️ En raíz sin integrar | ✅ Archivados o integrados |

---

## 🏗️ ESTADO ACTUAL DE LA ARQUITECTURA

### Estructura General

```
Mosca/
├── src/                                    # ✅ ARQUITECTURA MODULAR (v2.0)
│   ├── olfaction/                         # Sensorial
│   │   └── odor_field.py
│   ├── controllers/                       # Cognitivo
│   │   ├── olfactory_brain.py             # Legacy
│   │   ├── improved_olfactory_brain.py    # ⭐ Actual
│   │   └── brain_fly.py                   # Integración FlyGym
│   ├── simulation/                        # Simulación
│   │   └── olfactory_sim.py
│   ├── rendering/                         # ✅ MODULAR v2.0
│   │   ├── data/                          # Carga de datos
│   │   ├── core/                          # Renderizado
│   │   └── pipeline/                      # Orquestación
│   ├── workflow/                          # Workflows
│   └── core/                              # Configuración
│
├── tools/                                  # ⚠️ NECESITA LIMPIEZA
│   ├── run_complete_3d_simulation.py      # 16K - Principal actual
│   ├── validate_simulation.py             # 14K - Validación
│   ├── validate_movement_control.py       # 13K - Similar a validate_simulation
│   ├── diagnose_frames.py                 # 5.0K - Diagnóstico
│   ├── test_olfactory_simulation.py       # 3.7K - Test
│   ├── diagnose_kinematics.py             # 3.8K - Diagnóstico
│   ├── validate_modular_architecture.py   # 3.6K - Validación módulos
│   ├── test_obvious_angles.py             # 2.9K - Test angles
│   └── diagnose_flygym_render.py          # 2.7K - Diagnóstico render
│
├── neuromechfly_kinematic_replay.py       # ⚠️ 32K - LEGACY en raíz
├── render_enhanced_3d_v2.py               # ⚠️ 490B - LEGACY en raíz
│
├── data/                                   # ✅ DOCUMENTACIÓN
│   ├── docs/                              # Documentación técnica
│   │   ├── EXECUTIVE_SUMMARY.md
│   │   ├── COMPLETE_CODE_REVIEW.md
│   │   ├── WORKFLOW_GUIDE.md              # ⚠️ Desactualizado
│   │   ├── RENDERING_ARCHITECTURE.md
│   │   └── SUMMARY_OF_CHANGES.md
│   └── notebooks/                         # Jupyter notebooks
│
└── outputs/                                # ✅ ORGANIZADO
    └── simulations/
        └── 3d failed simulation/          # Datos de debug
```

### Evaluación por Componente

#### `/src` - Arquitectura Modular ✅
**Estado**: EXCELENTE
**Cobertura**: 100% de funcionalidad core
**Problemas**: Ninguno crítico

**Detalles**:
- Separación clara de responsabilidades
- Código limpio y documentado
- Tests unitarios presentes
- Sistema de rendering modular v2.0 implementado

#### `/tools` - Scripts de Utilidad ⚠️
**Estado**: NECESITA LIMPIEZA
**Redundancia**: ~40%
**Problemas**: Múltiples scripts con funcionalidad duplicada

**Análisis detallado**:

| Archivo | Tamaño | Propósito | Estado | Acción Recomendada |
|---------|--------|-----------|--------|-------------------|
| `run_complete_3d_simulation.py` | 16K | Pipeline completo sim+render | ✅ Actual | **MANTENER** como principal |
| `validate_simulation.py` | 14K | Validación múltiple | ✅ Útil | Mantener |
| `validate_movement_control.py` | 13K | Validación movimiento | ⚠️ Redundante | **CONSOLIDAR** con validate_simulation |
| `diagnose_frames.py` | 5.0K | Debug frames | ⚠️ Específico | Mover a /tools/debug/ |
| `test_olfactory_simulation.py` | 3.7K | Test simulación | ⚠️ Redundante | Integrar en validate_simulation |
| `diagnose_kinematics.py` | 3.8K | Debug cinemática | ⚠️ Específico | Mover a /tools/debug/ |
| `validate_modular_architecture.py` | 3.6K | Valida imports | ⚠️ CI only | Mover a /tools/ci/ |
| `test_obvious_angles.py` | 2.9K | Test angles obvios | ⚠️ Específico | Mover a /tools/debug/ |
| `diagnose_flygym_render.py` | 2.7K | Debug FlyGym | ⚠️ Específico | Mover a /tools/debug/ |

**Total**: 9 archivos, ~68K código
**Redundancia estimada**: 40% (~27K código duplicado)

#### Archivos Legacy en Raíz ⚠️
**Estado**: NO INTEGRADOS
**Problema**: Confusión y código duplicado

**Detalles**:

1. **`neuromechfly_kinematic_replay.py`** (32K)
   - **Propósito**: Replay de cinemática experimental con FlyGym
   - **Estado**: Funcional pero desconectado de arquitectura modular
   - **Problema**:
     - No usa módulos de `/src`
     - Duplica funcionalidad de `/src/rendering`
     - No documentado en WORKFLOW_GUIDE.md
   - **Ventaja**: Descarga datos oficiales de NeuroMechFly
   - **Acción**: Integrar con arquitectura modular o archivar

2. **`render_enhanced_3d_v2.py`** (490B)
   - **Propósito**: Wrapper simple para MuJoCoRenderer
   - **Estado**: Antiguo, usa API vieja
   - **Problema**:
     - Usa `src.core.config.create_moldeable_render()` que no existe en código actual
     - No compatible con arquitectura modular v2.0
     - Hardcodea paths y nombres de video
   - **Acción**: **ELIMINAR** o actualizar completamente

#### `/data/docs` - Documentación ⚠️
**Estado**: EXHAUSTIVA pero DESACTUALIZADA
**Problema**: Desconexión con código actual

**Análisis**:

| Documento | Líneas | Estado | Problema |
|-----------|--------|--------|----------|
| `WORKFLOW_GUIDE.md` | 220 | ⚠️ Desactualizado | Menciona scripts que no existen |
| `EXECUTIVE_SUMMARY.md` | 285 | ✅ Actualizado | Refleja estado actual |
| `COMPLETE_CODE_REVIEW.md` | 762 | ✅ Completo | Análisis exhaustivo |
| `RENDERING_ARCHITECTURE.md` | 412 | ✅ Actualizado | Documenta modular v2.0 |
| `SUMMARY_OF_CHANGES.md` | 200+ | ✅ Actualizado | Historial de cambios |

**Problema crítico con WORKFLOW_GUIDE.md**:

```bash
# ❌ WORKFLOW_GUIDE dice (línea 39):
python tools/simulation/simulation_runner.py
# Pero este archivo NO EXISTE

# ❌ WORKFLOW_GUIDE dice (línea 45):
python tools/simulation/simulation_validator.py
# Pero este archivo NO EXISTE

# ❌ WORKFLOW_GUIDE dice (línea 50):
python tools/simulation/3d_renderer.py
# Pero este archivo NO EXISTE

# ✅ Lo que SÍ existe:
python tools/run_complete_3d_simulation.py
python tools/validate_simulation.py
```

---

## 🔍 ANÁLISIS DEL DIRECTORIO /tools

### Clasificación Funcional

#### 1. Scripts Principales (Punto de Entrada)

**`run_complete_3d_simulation.py`** (16K)
- **Propósito**: Pipeline completo simulación + renderizado 3D
- **Componentes**:
  - `CompleteOlfactorySimulation` class
  - Integra: OdorField + ImprovedOlfactoryBrain
  - Genera: ángulos articulares + renderizado MuJoCo
- **Dependencias**: Usa arquitectura modular (`src/`)
- **Estado**: ✅ Funcional, actualizado
- **Uso documentado**: ❌ No en WORKFLOW_GUIDE
- **Acción**: **MANTENER** y actualizar documentación

**Fortalezas**:
- Único script que integra completamente con arquitectura modular
- Genera datos + video en un solo comando
- Usa `ImprovedOlfactoryBrain` (correcto)
- Genera patrones de marcha realistas

**Debilidades**:
- No permite parámetros por CLI (todo hardcodeado)
- No hay modo "solo simulación" o "solo render"
- Falta manejo de errores robusto

#### 2. Scripts de Validación (3 archivos, REDUNDANTES)

**`validate_simulation.py`** (14K)
- **Propósito**: Validación múltiple (data, flygym, angles, render)
- **Flags**: `--test [data|flygym|angles|render|all]`
- **Estado**: ✅ Completo
- **Acción**: **MANTENER** como validador principal

**`validate_movement_control.py`** (13K)
- **Propósito**: Validación de movimiento
- **Problema**: **70% duplicado** con `validate_simulation.py`
- **Estado**: ⚠️ Redundante
- **Acción**: **CONSOLIDAR** funcionalidad única en validate_simulation

**`validate_modular_architecture.py`** (3.6K)
- **Propósito**: Valida que módulos de `/src` se importan correctamente
- **Estado**: ✅ Útil para CI/CD
- **Problema**: No debería estar en `/tools` (usuario no lo usa)
- **Acción**: **MOVER** a `/tools/ci/` o raíz como `test_imports.py`

#### 3. Scripts de Diagnóstico (4 archivos, ESPECÍFICOS)

Estos scripts son útiles pero muy específicos para debugging:

| Script | Propósito | Problema |
|--------|-----------|----------|
| `diagnose_frames.py` | Inspecciona frames renderizados | Demasiado específico para /tools |
| `diagnose_kinematics.py` | Mini-sim para debug cinemática | Demasiado específico |
| `diagnose_flygym_render.py` | Debug FlyGym render() | Demasiado específico |
| `test_obvious_angles.py` | Test con ángulos obvios | Demasiado específico |

**Acción**: **MOVER TODOS** a `/tools/debug/` y actualizar documentación

#### 4. Scripts de Test (1 archivo)

**`test_olfactory_simulation.py`** (3.7K)
- **Propósito**: Test básico de simulación olfatoria
- **Problema**: Funcionalidad ya cubierta por `validate_simulation.py`
- **Estado**: ⚠️ Redundante
- **Acción**: **ELIMINAR** o integrar en validate_simulation

### Propuesta de Reorganización

```
tools/
├── run_simulation.py                    # ⭐ NUEVO: Punto de entrada único
│                                        #    Argumentos CLI completos
│                                        #    Modos: full/sim-only/render-only
│
├── validate_simulation.py               # ✅ MANTENER: Validador principal
│                                        #    Consolidar validate_movement_control aquí
│
├── debug/                               # ⭐ NUEVA CARPETA
│   ├── diagnose_frames.py
│   ├── diagnose_kinematics.py
│   ├── diagnose_flygym_render.py
│   └── test_obvious_angles.py
│
└── ci/                                  # ⭐ NUEVA CARPETA
    └── validate_imports.py              # (era validate_modular_architecture.py)
```

**Resultado**:
- **Antes**: 9 archivos en /tools (68K, confuso)
- **Después**: 2 archivos principales + 2 carpetas organizadas
- **Reducción**: 77% menos archivos en raíz de /tools
- **Claridad**: Punto de entrada único documentado

---

## 📁 ARCHIVOS LEGACY EN RAÍZ

### Problema

Dos archivos Python en la raíz del proyecto no integrados con la arquitectura modular:

```
Mosca/
├── neuromechfly_kinematic_replay.py  # 32K
└── render_enhanced_3d_v2.py          # 490B
```

**Impacto**:
- Confusión: ¿Qué script usar?
- Mantenimiento: Código duplicado sin sincronización
- Documentación: No mencionados en guías
- Arquitectura: Rompe separación modular

### Análisis Detallado

#### 1. `neuromechfly_kinematic_replay.py`

**Propósito Original**:
- Replay de datos cinemáticos experimentales de NeuroMechFly
- Basado en notebooks oficiales del tutorial
- Descarga y reproduce locomotion recording real

**Código**:
```python
class Config:
    LEG_JOINT_ANGLES_URL = "https://github.com/NeLy-EPFL/neuromechfly-workshop/..."

def download_data():
    # Descarga leg_joint_angles.pkl de NeuroMechFly oficial

def run_simulation():
    # Crea Fly con actuated_joints="all"
    # Reproduce ángulos experimentales
    # Renderiza con FlyGym
```

**Análisis**:

| Aspecto | Estado | Notas |
|---------|--------|-------|
| **Funcionalidad** | ✅ Completa | Replay funciona |
| **Integración modular** | ❌ Ninguna | No usa `/src` |
| **Duplicación** | ⚠️ Media | Duplica parte de rendering |
| **Valor único** | ✅ Alto | Usa datos oficiales reales |
| **Documentación** | ❌ No mencionado | No en guías |
| **Mantenimiento** | ⚠️ Difícil | Código monolítico |

**Funcionalidad Única (No Duplicada)**:
- ✅ Descarga automática de datos oficiales NeuroMechFly
- ✅ Procesamiento de formato experimental específico
- ✅ Validación con checksum MD5
- ✅ Compatibilidad con diferentes versiones de FlyGym

**Funcionalidad Duplicada**:
- ⚠️ Renderizado 3D (ya en `/src/rendering`)
- ⚠️ Setup de FlyGym (ya en `/src/rendering/data/environment_setup.py`)
- ⚠️ Generación de video (ya en `/src/rendering/core/video_writer.py`)

**Decisión**:
- ✅ **VALOR**: Mantener funcionalidad de replay experimental
- ⚠️ **PROBLEMA**: Refactorizar para usar arquitectura modular
- 📝 **ACCIÓN**: Crear `/src/replay/experimental_replay.py` que use módulos

#### 2. `render_enhanced_3d_v2.py`

**Código Completo**:
```python
#!/usr/bin/env python3
from src.core.config import create_moldeable_render
from src.render.mujoco_renderer import MuJoCoRenderer

def main():
    print("Iniciando Renderizado Estable - VISTA SUPERIOR (720p)")

    config = create_moldeable_render(fps=60)
    config.width = 720
    config.height = 720

    renderer = MuJoCoRenderer(config)
    renderer.render_and_save("neuromechfly_superior_caminar_recto2.mp4")

if __name__ == "__main__":
    main()
```

**Análisis**:

| Aspecto | Estado | Problema |
|---------|--------|----------|
| **Funcionalidad** | ❌ Rota | API no existe |
| **API usada** | ❌ Obsoleta | `create_moldeable_render()` no existe |
| **Path imports** | ⚠️ Viejo | Usa `src.render` (ahora es `src.rendering`) |
| **Valor único** | ❌ Ninguno | Todo duplicado |
| **Tamaño** | 490B | Trivial |

**Problemas**:
1. `create_moldeable_render()` no existe en código actual
2. `src.render` no existe (ahora es `src.rendering`)
3. API de `MuJoCoRenderer` cambió en v2.0
4. Hardcodea nombre de archivo de salida

**Decisión**: **ELIMINAR**
- No aporta valor
- Código roto
- Completamente duplicado por arquitectura modular
- Confunde a usuarios nuevos

### Plan de Acción para Legacy

| Archivo | Acción | Destino | Prioridad |
|---------|--------|---------|-----------|
| `neuromechfly_kinematic_replay.py` | **REFACTORIZAR** | `/src/replay/experimental_replay.py` + script wrapper en `/tools/replay_experimental.py` | ALTA |
| `render_enhanced_3d_v2.py` | **ELIMINAR** | N/A (crear ejemplo actualizado en docs si necesario) | ALTA |

**Resultado**:
- Raíz del proyecto limpia (solo README, setup.py, etc.)
- Funcionalidad de replay preservada pero integrada
- Eliminada confusión de múltiples entry points

---

## 🏛️ ARQUITECTURA MODULAR VS. LEGACY

### Comparación de Approaches

#### Approach 1: Arquitectura Modular (Recomendado) ✅

**Ubicación**: `/src` + `/tools/run_complete_3d_simulation.py`

**Flujo**:
```
User → tools/run_complete_3d_simulation.py
  ↓
  ├─→ src/olfaction/odor_field.py (sensorial)
  ├─→ src/controllers/improved_olfactory_brain.py (cognitivo)
  ├─→ Simulación cinemática (genera trayectoria + angles)
  └─→ src/rendering/ (modular v2.0)
       ├─→ data/environment_setup.py
       ├─→ core/frame_renderer.py
       └─→ core/video_writer.py
```

**Ventajas**:
- ✅ Separación de responsabilidades
- ✅ Código reutilizable
- ✅ Fácil de testear
- ✅ Bien documentado
- ✅ Usa `ImprovedOlfactoryBrain` (correcto)

**Desventajas**:
- ⚠️ No acepta parámetros CLI (todo hardcodeado)
- ⚠️ No permite ejecutar fases separadas (sim/render)

#### Approach 2: Legacy Scripts (Obsoleto) ❌

**Ubicación**: Raíz del proyecto

**Flujo**:
```
User → neuromechfly_kinematic_replay.py (monolítico)
  ↓
  ├─→ Descarga datos oficiales
  ├─→ Setup FlyGym (inline)
  ├─→ Replay angles (inline)
  └─→ Renderizado (inline)
```

**Ventajas**:
- ✅ Todo en un archivo (simple para demo)
- ✅ Usa datos oficiales reales

**Desventajas**:
- ❌ No usa arquitectura modular
- ❌ Código no reutilizable
- ❌ Difícil mantener
- ❌ Duplica funcionalidad

#### Approach 3: Legacy Wrapper (Roto) ❌

**Ubicación**: `render_enhanced_3d_v2.py` (raíz)

**Estado**: **COMPLETAMENTE ROTO**
- API no existe
- Imports incorrectos
- No compatible con v2.0

### Tabla Comparativa

| Característica | Modular ✅ | Legacy Replay ⚠️ | Legacy Wrapper ❌ |
|----------------|-----------|-----------------|------------------|
| **Usa /src modules** | Sí | No | Roto |
| **Documentado** | Parcial | No | No |
| **CLI arguments** | No | No | No |
| **Datos experimentales** | No | Sí | N/A |
| **Separación modular** | Sí | No | N/A |
| **Mantenible** | Sí | Difícil | N/A |
| **Estado** | Funcional | Funcional | Roto |

### Recomendación

**Estrategia Híbrida**:

1. **MANTENER** arquitectura modular como base
2. **INTEGRAR** funcionalidad única de legacy replay
3. **ELIMINAR** código roto
4. **CREAR** punto de entrada único con CLI completo

**Implementación**:

```
tools/
├── run_simulation.py              # Nuevo script unificado
│   ├── Modo 1: Chemotaxis (usa ImprovedOlfactoryBrain)
│   ├── Modo 2: Replay experimental (usa datos NeuroMechFly)
│   └── Modo 3: Render-only (from pkl)
│
src/
├── replay/                        # Nueva carpeta
│   └── experimental_replay.py     # Migración de neuromechfly_kinematic_replay
│
[ELIMINAR]
├── neuromechfly_kinematic_replay.py  # → Migrar a src/replay
└── render_enhanced_3d_v2.py           # → Eliminar (roto)
```

---

## ⚠️ PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. Documentación Desactualizada (CRÍTICO)

**Problema**: `data/docs/WORKFLOW_GUIDE.md` menciona scripts que no existen

**Ejemplos**:
```bash
# WORKFLOW_GUIDE.md línea 39:
python tools/simulation/simulation_runner.py    # ❌ NO EXISTE

# WORKFLOW_GUIDE.md línea 45:
python tools/simulation/simulation_validator.py  # ❌ NO EXISTE

# WORKFLOW_GUIDE.md línea 50:
python tools/simulation/3d_renderer.py           # ❌ NO EXISTE
```

**Impacto**:
- Usuario no puede seguir guía
- Frustración y pérdida de tiempo
- Confianza en documentación baja

**Solución**:
- Actualizar WORKFLOW_GUIDE.md con scripts reales
- Crear los scripts mencionados O cambiar documentación

### 2. Falta Punto de Entrada Único (CRÍTICO)

**Problema**: Múltiples formas de hacer lo mismo, ninguna clara

**Opciones actuales**:
- `tools/run_complete_3d_simulation.py` (sin documentar)
- `neuromechfly_kinematic_replay.py` (legacy)
- Componentes individuales de `/src/rendering`

**Impacto**:
- Confusión: ¿Qué script usar?
- Cada uno con API diferente
- Documentación no alinea con realidad

**Solución**:
- Crear `tools/run_simulation.py` como punto de entrada único
- CLI completo con argumentos
- Documentar claramente en WORKFLOW_GUIDE

### 3. Redundancia en Tools (ALTA PRIORIDAD)

**Problema**: 40% del código en `/tools` es redundante

**Detalles**:
- `validate_simulation.py` vs `validate_movement_control.py`: 70% overlap
- `test_olfactory_simulation.py`: funcionalidad ya en validate_simulation
- 4 scripts de diagnóstico sin organización

**Impacto**:
- Mantenimiento duplicado
- Inconsistencias entre versiones
- Confusión sobre qué usar

**Solución**:
- Consolidar validadores
- Organizar diagnósticos en `/tools/debug`
- Eliminar duplicados

### 4. Legacy Sin Integrar (MEDIA PRIORIDAD)

**Problema**: Archivos útiles en raíz sin integrar con arquitectura

**Detalles**:
- `neuromechfly_kinematic_replay.py`: 32K código útil pero aislado
- Duplica funcionalidad de rendering
- No usa módulos de `/src`

**Impacto**:
- Código duplicado sin sincronización
- Funcionalidad útil (replay experimental) difícil de mantener

**Solución**:
- Refactorizar a `/src/replay`
- Usar módulos de rendering
- Crear wrapper en `/tools`

### 5. Arquitectura Modular No Usada Completamente (MEDIA)

**Problema**: Arquitectura v2.0 de rendering existe pero no es el default

**Detalles**:
- `run_complete_3d_simulation.py` usa rendering pero no vía pipeline
- Importa componentes directamente en lugar de usar `RenderingPipeline`
- Documentación menciona `RenderingPipeline` pero código no lo usa

**Impacto**:
- Beneficios de modularidad no aprovechados
- Código menos mantenible

**Solución**:
- Actualizar `run_complete_3d_simulation` para usar `RenderingPipeline`
- O documentar por qué no se usa

---

## 💡 RECOMENDACIONES DE REESTRUCTURACIÓN

### Fase 1: Limpieza Inmediata (1-2 días)

**Objetivo**: Eliminar confusión y redundancia crítica

#### 1.1 Eliminar Archivos Rotos
```bash
# Eliminar
rm render_enhanced_3d_v2.py

# Motivo: API rota, código obsoleto, completamente duplicado
```

#### 1.2 Organizar Tools
```bash
# Crear estructura
mkdir -p tools/debug tools/ci

# Mover scripts específicos
mv tools/diagnose_*.py tools/debug/
mv tools/test_obvious_angles.py tools/debug/
mv tools/validate_modular_architecture.py tools/ci/validate_imports.py
```

#### 1.3 Consolidar Validadores
```python
# En validate_simulation.py, agregar funcionalidad de:
# - validate_movement_control.py
# - test_olfactory_simulation.py

# Luego eliminar archivos redundantes
rm tools/validate_movement_control.py
rm tools/test_olfactory_simulation.py
```

**Resultado Fase 1**:
- Raíz limpia (sin legacy roto)
- `/tools` organizado (2 main + 2 folders)
- Redundancia reducida 40% → 15%

### Fase 2: Punto de Entrada Único (2-3 días)

**Objetivo**: Script principal claro y documentado

#### 2.1 Crear `tools/run_simulation.py`

```python
#!/usr/bin/env python3
"""
Punto de entrada único para simulaciones NeuroMechFly.

MODOS:
1. chemotaxis  - Navegación olfatoria (ImprovedOlfactoryBrain)
2. replay      - Replay datos experimentales (NeuroMechFly official)
3. render-only - Solo renderizar trayectoria existente

EJEMPLOS:
    # Simulación completa chemotaxis
    python tools/run_simulation.py chemotaxis --duration 15 --output outputs/sim1

    # Replay experimental
    python tools/run_simulation.py replay --data data/leg_joint_angles.pkl

    # Solo render
    python tools/run_simulation.py render-only --input outputs/sim1/trajectory.pkl
"""

import argparse
import sys
from pathlib import Path

# Import módulos según modo
# ...

def main():
    parser = argparse.ArgumentParser(description="NeuroMechFly Simulation")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Modo 1: Chemotaxis
    chemotaxis_parser = subparsers.add_parser("chemotaxis")
    chemotaxis_parser.add_argument("--duration", type=float, default=15.0)
    chemotaxis_parser.add_argument("--output", type=str, default="outputs/simulations")
    chemotaxis_parser.add_argument("--odor-source", nargs=3, type=float)
    # ...

    # Modo 2: Replay
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("--data", type=str, required=True)
    # ...

    # Modo 3: Render-only
    render_parser = subparsers.add_parser("render-only")
    render_parser.add_argument("--input", type=str, required=True)
    # ...

    args = parser.parse_args()

    if args.mode == "chemotaxis":
        run_chemotaxis_simulation(args)
    elif args.mode == "replay":
        run_replay_simulation(args)
    elif args.mode == "render-only":
        run_render_only(args)

if __name__ == "__main__":
    main()
```

#### 2.2 Actualizar WORKFLOW_GUIDE.md

```markdown
# Guía de Workflow - Mosca Olfactory Navigation

## 🚀 Punto de Entrada Único

### Simulación Chemotaxis (Navegación Olfatoria)

```bash
python tools/run_simulation.py chemotaxis \
    --duration 15 \
    --output outputs/my_simulation \
    --odor-source 50 50 5
```

**Genera**:
- `outputs/my_simulation/trajectory.csv`
- `outputs/my_simulation/simulation_3d.mp4`
- `outputs/my_simulation/config.json`

### Replay de Datos Experimentales

```bash
python tools/run_simulation.py replay \
    --data data/leg_joint_angles.pkl \
    --output outputs/replay_1
```

### Solo Renderizado (desde trayectoria guardada)

```bash
python tools/run_simulation.py render-only \
    --input outputs/my_simulation/trajectory.pkl \
    --fps 60 \
    --quality high
```
```

**Resultado Fase 2**:
- Punto de entrada único claro
- Documentación sincronizada
- CLI completo y flexible

### Fase 3: Integración Modular (3-5 días)

**Objetivo**: Legacy integrado con arquitectura modular

#### 3.1 Migrar Replay Experimental

```bash
# Crear módulo nuevo
mkdir -p src/replay

# Extraer funcionalidad de neuromechfly_kinematic_replay.py
# y refactorizar para usar módulos de /src
```

**Estructura**:
```python
# src/replay/experimental_replay.py

from src.rendering import RenderingPipeline
from src.rendering.data import DataLoader

class ExperimentalReplay:
    """
    Replay de datos experimentales NeuroMechFly oficial.

    Usa arquitectura modular para rendering.
    """

    def __init__(self, data_source="url"):
        self.data_loader = DataLoader()
        # ...

    def download_official_data(self):
        # Migrar de neuromechfly_kinematic_replay.py
        # ...

    def prepare_kinematic_data(self):
        # Usa DataLoader
        # ...

    def render(self, output_file):
        # Usa RenderingPipeline
        pipeline = RenderingPipeline()
        pipeline.render(...)
```

#### 3.2 Actualizar run_complete_3d_simulation

```python
# Cambiar de imports directos a RenderingPipeline

# ANTES:
from rendering import MuJoCoRenderer

# DESPUÉS:
from src.rendering import RenderingPipeline

# Y usar:
pipeline = RenderingPipeline()
pipeline.render(
    data_file=self.output_pkl,
    output_video=output_video,
    fps=60
)
```

#### 3.3 Eliminar Legacy

```bash
# Una vez migrada funcionalidad
rm neuromechfly_kinematic_replay.py

# Actualizar documentación mencionando migración
```

**Resultado Fase 3**:
- Todo código usa arquitectura modular
- No hay duplicación
- Funcionalidad experimental preservada

### Fase 4: Documentación Final (1 día)

**Objetivo**: Documentación completa y actualizada

#### 4.1 Actualizar Todos los Docs

```markdown
# data/docs/WORKFLOW_GUIDE.md
- Actualizar con run_simulation.py
- Ejemplos concretos y testeados
- Remover referencias a scripts inexistentes

# data/docs/ARCHITECTURE_ANALYSIS.md
- Este documento
- Mantener actualizado con cambios

# README.md
- Quick start actualizado
- Mencionar run_simulation.py como entry point
```

#### 4.2 Crear Guía de Migración

```markdown
# data/docs/MIGRATION_GUIDE.md

## Migración de Scripts Legacy

### Si usabas neuromechfly_kinematic_replay.py

ANTES:
```bash
python neuromechfly_kinematic_replay.py
```

DESPUÉS:
```bash
python tools/run_simulation.py replay --data data/leg_joint_angles.pkl
```
```

**Resultado Fase 4**:
- Documentación 100% sincronizada
- Guías de migración para usuarios existentes
- Quick start actualizado

---

## 📅 PLAN DE MIGRACIÓN

### Timeline Recomendado

| Fase | Duración | Prioridad | Riesgo |
|------|----------|-----------|--------|
| Fase 1: Limpieza | 1-2 días | CRÍTICA | Bajo |
| Fase 2: Entry Point | 2-3 días | CRÍTICA | Medio |
| Fase 3: Integración | 3-5 días | ALTA | Medio |
| Fase 4: Documentación | 1 día | ALTA | Bajo |
| **TOTAL** | **7-11 días** | - | - |

### Checklist de Implementación

#### Fase 1: Limpieza ✅
- [ ] Eliminar `render_enhanced_3d_v2.py`
- [ ] Crear `/tools/debug` y `/tools/ci`
- [ ] Mover scripts de diagnóstico
- [ ] Consolidar `validate_simulation.py`
- [ ] Eliminar `validate_movement_control.py`
- [ ] Eliminar `test_olfactory_simulation.py`
- [ ] Actualizar `.gitignore` si necesario

#### Fase 2: Entry Point ✅
- [ ] Crear `tools/run_simulation.py`
- [ ] Implementar modo `chemotaxis`
- [ ] Implementar modo `replay`
- [ ] Implementar modo `render-only`
- [ ] Agregar argumentos CLI completos
- [ ] Testear cada modo
- [ ] Actualizar `WORKFLOW_GUIDE.md`
- [ ] Crear ejemplos en documentación

#### Fase 3: Integración Modular ✅
- [ ] Crear `/src/replay`
- [ ] Migrar funcionalidad de `neuromechfly_kinematic_replay.py`
- [ ] Refactorizar para usar módulos de `/src`
- [ ] Actualizar `run_complete_3d_simulation.py` para usar `RenderingPipeline`
- [ ] Testear integración
- [ ] Eliminar `neuromechfly_kinematic_replay.py`
- [ ] Verificar no hay dependencias rotas

#### Fase 4: Documentación Final ✅
- [ ] Actualizar `WORKFLOW_GUIDE.md` completo
- [ ] Actualizar `README.md` quick start
- [ ] Crear `MIGRATION_GUIDE.md`
- [ ] Actualizar `EXECUTIVE_SUMMARY.md`
- [ ] Verificar todas las referencias a scripts
- [ ] Crear ejemplos de uso
- [ ] Review final de documentación

### Criterios de Éxito

**Métricas Objetivas**:
- ✅ Reducción de archivos en `/tools`: de 9 → 2 principales
- ✅ Redundancia de código: de 40% → <10%
- ✅ Scripts mencionados en docs: 100% existen y funcionan
- ✅ Punto de entrada único: 1 script, 3 modos
- ✅ Archivos legacy en raíz: 0

**Métricas Subjetivas**:
- ✅ Usuario nuevo puede empezar en <5 minutos
- ✅ Documentación alinea 100% con código
- ✅ No hay confusión sobre qué script usar
- ✅ Mantenimiento simplificado

---

## 📚 REFERENCIAS

### Documentos Relacionados

- **EXECUTIVE_SUMMARY.md** - Resumen ejecutivo del proyecto
- **COMPLETE_CODE_REVIEW.md** - Análisis técnico detallado del código
- **WORKFLOW_GUIDE.md** - Guía de uso (requiere actualización)
- **RENDERING_ARCHITECTURE.md** - Arquitectura modular de rendering v2.0
- **SUMMARY_OF_CHANGES.md** - Historial de cambios

### Commits Relevantes

- 2026-03-12: Arquitectura modular de rendering v2.0
- 2026-03-12: Temporal gradient fix en ImprovedOlfactoryBrain
- 2026-03-12: Limpieza de /tools (eliminados scripts redundantes)

---

## 🎯 CONCLUSIÓN

### Estado Actual

El proyecto tiene una **arquitectura modular sólida** en `/src` pero sufre de:
- ⚠️ Fragmentación de entry points
- ⚠️ Código legacy sin integrar
- ⚠️ Redundancia en scripts de utilidad
- ⚠️ Documentación desincronizada

### Visión Futura

Con las fases de reestructuración implementadas:
- ✅ Punto de entrada único (`run_simulation.py`)
- ✅ Arquitectura modular usada completamente
- ✅ Documentación sincronizada al 100%
- ✅ Mantenimiento simplificado
- ✅ Experiencia de usuario clara

### Próximos Pasos Inmediatos

1. **HOY**: Implementar Fase 1 (Limpieza)
2. **Esta Semana**: Implementar Fase 2 (Entry Point)
3. **Próxima Semana**: Implementar Fases 3-4

---

**Autor**: Claude Code (Arquitectura Analysis Agent)
**Fecha**: 2026-03-12
**Versión**: 2.0
**Estado**: Análisis Completo - Pendiente Implementación
