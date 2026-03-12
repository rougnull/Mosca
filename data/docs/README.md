# Documentación Técnica del Proyecto

Esta carpeta contiene la documentación técnica completa del proyecto Mosca - Navegación Olfatoria en Drosophila.

### Reglas Técnicas Obligatorias - Estándares de Arquitectura

#### 1. GESTIÓN DE ARCHIVOS Y CARPETAS

**1.1 Estructura de Directorios:**
- `/tools`: Solo scripts FUNCIONALES con una responsabilidad ÚNICA y CLARA
  - 1 punto de entrada principal por módulo (ej: `simulate_chemotaxis.py`)
  - Scripts de debug van a `/tools/debug/` (no en raíz de tools)
  - No crear carpetas temáticas (ej: "3d_simulations", "analysis_tools")
  - Máximo 1 archivo por funcionalidad; si necesitas variantes, parámetros en CLI
  
- `/outputs/simulations`: ÚNICA carpeta para resultados de simulaciones
  - Estructura: `/outputs/simulations/{TIPO_SIMULACION}/{TIMESTAMP}/`
  - Tipos válidos: `chemotaxis_3d/`, `olfactory_2d/`, `behavioral_test/`
  - No crear subdirectories arbitrarias (ej: `3d_simulations/` está PROHIBIDO)
  - Incluir metadatos en JSON/YAML con cada simulación

- `/outputs/debug`: ÚNICA carpeta para logs y datos diagnosticos
  - Solo archivos generados durante debugging/testing
  - Usar timestamps en nombres: `debug_2026-03-12_14-32.log`

- `/data/docs`: Documentación técnica ÚNICAMENTE
  - Solo `.md` que describen implementaciones y cambios de arquitectura
  - Prohibido: guías de uso, tutoriales, "cambios de sesión", ejemplos
  - Mantener lista actualizada de módulos en `IMPLEMENTATION_SUMMARY.md`

**1.2 Gestión de Redundancia:**
- **PROHIBIDO**: Crear múltiples scripts con el mismo propósito
- **OBLIGATORIO**: Combinar en 1 archivo principal con opciones CLI
- Ejemplo CORRECTO:
  ```python
  # tools/validate_simulation.py (archivo ÚNICO con todos los tests)
  if args.test == "angles":          # HABILITABLE
      test_angle_ranges()
  elif args.test == "flygym":        # HABILITABLE
      test_flygym_integration()
  elif args.test == "all":           # EJECUTAR TODO
      run_all_tests()
  ```
- Ejemplo INCORRECTO:
  ```
  tools/test_angles.py               # ❌ PROHIBIDO
  tools/test_flygym.py               # ❌ PROHIBIDO
  tools/test_behavior.py             # ❌ PROHIBIDO
  ```

#### 2. NAMINACIÓN Y CATEGORIZACIÓN DE SCRIPTS

**2.1 Convención de Nombres en /tools:**
```
simulate_*.py         - Scripts de simulación (ejecución principal)
process_*.py          - Transformación de datos/postprocessing
analyze_*.py          - Análisis de resultados
validate_*.py         - Testing y verificación
render_*.py           - Generación de visualizaciones
debug_*.py            - Herramientas de diagnóstico (ej: debug_angles.py)
```

**2.2 Punto de Entrada Único:**
- Para cada funcionalidad mayor, 1 script principal en `/tools`
- Variantes se controlan con argumentos CLI (`--option value`)
- NO copiar/modificar scripts sin cambiar el nombre (ej: `render_final.py`, `render_simple.py` → INCORRECTO)

#### 3. CONTROL DE VERSIONES Y OUTPUTS

**3.1 Outputs de Simulaciones:**
- Ruta obligatoria: `/outputs/simulations/{TIPO}/{TIMESTAMP}/`
- Archivos incluídos SIEMPRE:
  - `metadata.json` - Parámetros, versión código, timestamp
  - `simulation_data.pkl` - Datos brutos de la simulación
  - `video.mp4` - Visualización (si aplica)
  - `summary.txt` - Resumen de ejecución

**3.2 Ignorar git:**
- En `.gitignore` NO incluir `/outputs` ni `/data/debug`
- Todos los resultados deben compartirse en repositorio
- Ser selectivo: excluir solo archivos temporales (`.tmp`, `*.swp`)

#### 4. DOCUMENTACIÓN Y CAMBIOS DE CÓDIGO

**4.1 Documentar Cambios:**
- CADA cambio en arquitectura → actualizar `/data/docs/SUMMARY_OF_CHANGES.md`
- CADA nuevo script → describir en `/data/docs/IMPLEMENTATION_SUMMARY.md`
- Formato requerido:
  ```markdown
  ## Cambio: [Nombre módulo]
  - **Archivo**: ruta/archivo.py
  - **Cambio**: [Descripción técnica]
  - **Razón**: [Por qué fue necesario]
  - **Impacto**: [Qué otros módulos afecta]
  ```

**4.2 Prohibido:**
- ❌ Archivos `.md` de "guías de uso" o "tutoriales"
- ❌ Archivos `.md` documentando "cambios de sesión" del desarrollador
- ❌ Comentarios en código explicando "qué hizo el AI en sesión X"
- ✅ Documentar RESULTADOS TÉCNICOS y DECISIONES DE ARQUITECTURA únicamente

#### 5. VALIDACIÓN ANTES DE EJECUCIÓN

**5.1 Pre-ejecución (OBLIGATORIO):**
- [ ] Verificar ruta de output (siempre `/outputs/simulations/...`)
- [ ] Verificar no hay carpetas temáticas nuevas
- [ ] Verificar no hay scripts redundantes en `/tools`
- [ ] Verificar metadatos + logging en el script
- [ ] Ejecutar con `--dry-run` o verbose para validar comportamiento

**5.2 Post-ejecución (OBLIGATORIO):**
- [ ] Inspeccionar outputs generados (metadata.json, video.mp4, etc)
- [ ] Verificar duración video (> 0.5 segundos para video de movimiento)
- [ ] Verificar datos (shape, valores, no NaN)
- [ ] Documentar en `/data/docs/SUMMARY_OF_CHANGES.md` si hay cambios

#### 6. BUG TRACKING Y PROBLEMAS CONOCIDOS

**6.1 Renderizado FlyGym (CRÍTICO - 2026-03-12):**
- Problema: `SingleFlySimulation.render()` solo devuelve frame válido en step 0, después devuelve [None]
- Causa: Necesita configuración explícita de `render_mode` y cámara
- Estado: PENDIENTE - Investigar FlyGym version 0.2.7 docs
- Workaround actual: Duplicar último frame válido para frames posteriores
- Impacto: Videos no muestran movimiento (duración corta, frames estáticos)

**6.2 Inestabilidad Física MuJoCo (CRÍTICO - 2026-03-12):**
- Problema: Aplicar ángulos dinámicos desde pickle causa NaN/Inf en primeros steps
- Causa: Conflicto entre postura inicial "stretch" y ángulos del pickle
- Solución: Saltear primeros 10 frames para que simulación se estabilice
- Impacto: Video generado tiene gaps iniciales

## Archivos de Documentación

### 📊 EXECUTIVE_SUMMARY.md
**Resumen ejecutivo de alto nivel**

Contiene:
- Estado general del proyecto
- Hallazgos principales del code review
- Métricas de calidad antes/después
- Recomendaciones prioritizadas

**Audiencia**: Gestores de proyecto, investigadores principales

---

### 🔍 COMPLETE_CODE_REVIEW.md
**Análisis técnico exhaustivo (762 líneas)**

Contiene:
- Análisis completo de arquitectura
- Identificación de código duplicado
- Validación de parámetros biológicos
- Comparación con referencias bibliográficas
- Discrepancias técnicas
- Recomendaciones detalladas

**Audiencia**: Desarrolladores, científicos computacionales

---

### 🚀 WORKFLOW_GUIDE.md
**Guía práctica de uso**

Contiene:
- Qué script usar para cada tarea
- Workflows comunes
- Ejemplos de comandos
- Troubleshooting
- Parámetros recomendados

**Audiencia**: Usuarios del sistema, nuevos desarrolladores

---

### 📝 SUMMARY_OF_CHANGES.md
**Historial de cambios y mejoras**

Contiene:
- Cambios implementados en el code review
- Impacto de cada cambio
- Archivos modificados/eliminados
- Próximos pasos recomendados

**Audiencia**: Equipo de desarrollo, mantenedores

---

## Orden de Lectura Recomendado

### Para nuevos usuarios:
1. **WORKFLOW_GUIDE.md** - Aprende a usar el sistema
2. **EXECUTIVE_SUMMARY.md** - Entiende el proyecto globalmente
3. **README.md** (en raíz) - Documentación biológica y técnica

### Para desarrolladores:
1. **EXECUTIVE_SUMMARY.md** - Contexto general
2. **COMPLETE_CODE_REVIEW.md** - Análisis técnico detallado
3. **SUMMARY_OF_CHANGES.md** - Qué se cambió y por qué
4. **WORKFLOW_GUIDE.md** - Cómo ejecutar scripts

### Para científicos/investigadores:
1. **README.md** (en raíz) - Fundamentos biológicos
2. **EXECUTIVE_SUMMARY.md** - Hallazgos principales
3. **COMPLETE_CODE_REVIEW.md (Sección 7)** - Validación biológica

---

## Actualización

Esta documentación fue generada el **2026-03-12** como parte de un code review exhaustivo.

Para mantenerla actualizada:
- Actualizar **SUMMARY_OF_CHANGES.md** cuando se implementen mejoras
- Revisar **WORKFLOW_GUIDE.md** si se agregan nuevos scripts
- Actualizar **EXECUTIVE_SUMMARY.md** periódicamente con nuevos hallazgos

---

**Última actualización**: 2026-03-12
