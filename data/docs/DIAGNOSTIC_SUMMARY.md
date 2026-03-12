# Resumen del Diagnóstico - Problemas de Renderizado 3D

**Fecha**: 2026-03-12
**Estado**: ✅ ROOT CAUSE IDENTIFICADO

---

## 🎯 PROBLEMA PRINCIPAL

**La mosca se hunde en el suelo, rota 180° y aparece moviéndose a 1 fps**

---

## 🔍 ROOT CAUSE

### ARQUITECTURA HÍBRIDA INCORRECTA

El sistema actual tiene una **separación problemática** entre simulación y renderizado:

```
Simulación Cinemática        →      Renderizado Físico
(sin física, ángulos sintéticos)    (FlyGym con MuJoCo physics)
          ↓                                  ↓
    [PKL File]                         [Conflicto]
```

### Por qué falla:

1. **`run_complete_3d_simulation.py`** hace simulación CINEMÁTICA:
   - Integración manual: `pos += velocity * cos(heading) * dt`
   - **Z siempre constante (0.0)** ← No considera gravedad ni suelo
   - Genera ángulos articulares con **senos/cosenos simples** ← No físicamente válidos

2. **`mujoco_renderer.py`** trata de aplicar esos datos a FlyGym:
   - FlyGym **SÍ tiene física completa** (gravedad, colisiones, torques)
   - Los ángulos sintéticos **no soportan el peso del cuerpo**
   - El cuerpo **colapsa y se hunde**

---

## 📊 PROBLEMAS ESPECÍFICOS

### 1. Hundimiento en el Suelo
**Causa**: Z constante en cinemática + ángulos que no generan fuerza de soporte
- Línea `run_complete_3d_simulation.py:259`: `0.0` (Z nunca cambia)
- Cuando FlyGym aplica física → cuerpo cae por gravedad

### 2. Rotación 180°
**Causa**: Ángulos sintéticos no mantienen balance corporal
- Patas no coordinadas para balance
- Centro de masa no considerado
- Cuerpo rota por inestabilidad física

### 3. Movimiento a 1 FPS
**Causa**: Timestep mismatch + frames fallidos en renderizado
- Simulación @ 100Hz (dt=0.01s)
- Renderizado @ 60fps
- Muchos frames fallan por problemas físicos

### 4. Patas Rectas/Rígidas
**Causa**: Ángulos generados por `_generate_joint_angles_for_step()` son sintéticos
- No consideran contacto con suelo
- No consideran fuerzas de reacción
- Pattern tripod mal implementado

---

## ✅ SOLUCIÓN RECOMENDADA

### **Opción A: Usar FlyGym con Física desde el Principio**

En lugar de:
```
Cinemática → PKL → Renderizado Físico
```

Hacer:
```
FlyGym con Física → Renderizado Directo
```

**Ventajas**:
- ✅ Física correcta desde el inicio
- ✅ No hay conflicto cinemática-física
- ✅ Ángulos siempre válidos
- ✅ Balance automático
- ✅ Z posición calculada correctamente

**Implementación**:
1. Reescribir `run_complete_3d_simulation.py` para usar `SingleFlySimulation` desde inicio
2. Usar `BrainFly` con `ImprovedOlfactoryBrain`
3. Implementar `_motor_signal_to_action()` que convierte [forward, turn] → joint angles
4. Renderizar directamente desde la simulación

---

## 🔧 ARCHIVOS CLAVE

### Diagnóstico Completo
- **`data/docs/DIAGNOSTIC_SIMULATION_ISSUES.md`** - Análisis técnico detallado

### Código Problemático
- **`tools/run_complete_3d_simulation.py:256-260`** - Z constante
- **`tools/run_complete_3d_simulation.py:153-229`** - Ángulos sintéticos
- **`src/rendering/core/mujoco_renderer.py:168-238`** - Aplicación de ángulos inválidos

### Código a Implementar
- **`src/controllers/brain_fly.py`** - Necesita `_motor_signal_to_action()`
- **`tools/run_complete_3d_simulation_v2.py`** - Nueva versión con física completa

---

## 📝 PRÓXIMOS PASOS

1. **Implementar `_motor_signal_to_action()` en BrainFly**
   - Convertir [forward, turn] → joint angles
   - Usar CPG o tripod gait pattern

2. **Crear `run_complete_3d_simulation_v2.py`**
   - Usar FlyGym desde el inicio
   - Eliminar simulación cinemática

3. **Probar con simulación corta (5 segundos)**
   - Verificar que no se hunde
   - Verificar que no rota incorrectamente
   - Verificar movimiento suave

4. **Extender a simulación completa (15 segundos)**
   - Una vez verificado el comportamiento básico

---

## 🔗 DOCUMENTOS RELACIONADOS

- **`DIAGNOSTIC_SIMULATION_ISSUES.md`** - Diagnóstico técnico completo
- **`IMPLEMENTATION_3D_FIXES.md`** - Fixes previos (heading extraction)
- **`ARCHITECTURE_ANALYSIS.md`** - Análisis arquitectural del sistema
- **`SUMMARY_ANALYSIS.md`** - Resumen general del proyecto

---

**Diagnóstico por**: Claude Code
**Branch**: claude/analyze-code-and-documentation
