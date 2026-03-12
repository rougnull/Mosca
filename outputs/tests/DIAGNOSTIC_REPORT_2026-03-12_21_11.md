# Análisis de Simulación 2026-03-12_21_11

## Problemas Identificados

### 1. Forward Action Muy Bajo (Mean = 0.00085)

**Causa Raíz:** El temporal_gradient_gain está configurado en 10.0, pero los cambios de concentración son extremadamente pequeños.

**Datos:**
- Mean dC/dt: 5.8e-05 (extremadamente pequeño)
- temporal_gradient_gain = 10.0
- forward = clip(dC * 10, 0, 1)
- Resultado: forward = clip(5.8e-05 * 10, 0, 1) = 0.00058 ≈ 0

**Por qué los cambios son tan pequeños:**
1. La mosca apenas se mueve (forward ≈ 0)
2. Sin movimiento, no hay cambios significativos en la concentración
3. Sin cambios de concentración, no hay forward action
4. **BUCLE DE RETROALIMENTACIÓN NEGATIVA**

**Comparación con Test:**
- Test (200 pasos): forward mean = 0.016 (19x más alto)
- Simulación (50,000 pasos): forward mean = 0.00085
- La diferencia sugiere que el problema empeora con el tiempo

### 2. Z-Axis Cayendo Constantemente

**Trayectoria Z:**
```
Steps 0-1000:      Mean Z = 2.004mm
Steps 1000-10000:  Mean Z = 2.022mm
Steps 10000-20000: Mean Z = 1.718mm  ↓
Steps 20000-30000: Mean Z = 0.273mm  ↓↓↓
Steps 30000-40000: Mean Z = 0.261mm
Steps 40000-50000: Mean Z = 0.275mm
```

**Final: Z = 0.263mm (inicial era 1.783mm)**

**Estadísticas:**
- 63.3% de los pasos con Z < 0.5mm
- 63.3% de los pasos con Z < 0.3mm
- La mosca está casi en el suelo la mayor parte del tiempo

**Causa Raíz:** El CPG no genera suficiente soporte vertical. Posibles causas:
1. **Amplitude demasiado bajo cuando forward ≈ 0:**
   - `amplitude = 0.5 + 0.5 * abs(forward)`
   - Con forward ≈ 0: amplitude ≈ 0.5
   - Puede no ser suficiente para sostener el cuerpo

2. **Femur offset permanentemente flexionado:**
   - `offset = -0.8` rad (siempre flexionado)
   - En stance: `angle = -0.8 + amp * 0.3 = -0.8 + 0.15 = -0.65` rad
   - Las patas nunca se extienden lo suficiente para levantar el cuerpo

3. **Tibia puede no estar compensando:**
   - offset = 1.2 rad (extendido)
   - En stance: `angle = 1.2 - amp * 0.3 = 1.05` rad
   - Combinado con femur flexionado, la altura total es insuficiente

### 3. Concentración Cambia Muy Poco

**Datos:**
- Initial conc: 2.756
- Final conc: 5.668 (aumentó 2.91, ¡pero la mosca no avanza!)
- Max step change: 7.98e-03
- Min step change: -2.90e-03
- Mean step change: 5.82e-05

**Esto es paradójico:**
- La concentración AUMENTA significativamente (2.91 total)
- Pero los cambios step-by-step son minúsculos
- Sugiere que la mosca está moviéndose MUY lentamente

**Confirmación:**
- Distancia XY recorrida: 7.0mm en 50,000 pasos = 0.00014mm/paso
- En 5 segundos (50,000 pasos * 1e-4s), recorrió solo 7mm
- Velocidad: 1.4 mm/s (extremadamente lento para una mosca)

## Diagnóstico: Problemas Interconectados

Los tres problemas están relacionados:

```
Low forward → Minimal movement → Small dC/dt → Low forward
     ↓
   Low CPG amplitude → Sinking → Body close to ground → Movement restricted
     ↓
   Restricted movement → Even smaller dC/dt → Even lower forward
```

## Soluciones Propuestas

### Solución 1: Aumentar Temporal Gradient Gain

**Cambio sugerido:**
```python
temporal_gradient_gain = 10.0  # ANTES
temporal_gradient_gain = 100.0  # DESPUÉS (10x más sensible)
```

**Razón:**
- Con gain=10: necesita dC > 0.1 para forward=1.0
- Con gain=100: necesita dC > 0.01 para forward=1.0
- Actual dC promedio: 5.8e-05, max: 8e-03
- Con gain=100: forward = clip(8e-03 * 100, 0, 1) = 0.8 (¡mucho mejor!)

**Riesgo:** Puede hacer que la mosca sea demasiado sensible a ruido. Necesitamos probar.

### Solución 2: Aumentar Baseline CPG Amplitude

**Cambio sugerido en cpg_controller.py:**
```python
# ANTES:
amplitude = 0.5 + 0.5 * abs(forward)

# DESPUÉS:
amplitude = 0.7 + 0.3 * abs(forward)  # Baseline más alto
```

**Razón:**
- Cuando forward ≈ 0:
  - ANTES: amplitude = 0.5
  - DESPUÉS: amplitude = 0.7 (40% más alto)
- Esto da más movimiento de patas incluso sin comando forward
- Debería prevenir el hundimiento

### Solución 3: Ajustar Femur Offset para Mejor Soporte

**Cambio sugerido en cpg_controller.py:**
```python
# ANTES:
offset = -0.8  # Permanentemente flexionado

# DESPUÉS:
offset = -0.6  # Más extendido, mejor soporte
```

**En stance:**
- ANTES: angle = -0.8 + 0.15 = -0.65 rad
- DESPUÉS: angle = -0.6 + 0.15 = -0.45 rad (más extendido)

### Solución 4: Aumentar Bootstrap Inicial

**Ya está en 0.5, pero podríamos aumentar temporalmente:**
```python
conc_change = 1.0  # Más fuerte para superar inercia inicial
```

## Recomendaciones de Implementación

1. **Prioridad Alta:** Aumentar temporal_gradient_gain de 10.0 a 50.0 o 100.0
2. **Prioridad Alta:** Aumentar baseline CPG amplitude de 0.5 a 0.7
3. **Prioridad Media:** Ajustar femur offset de -0.8 a -0.6
4. **Prioridad Baja:** Aumentar bootstrap (ya está razonablemente alto)

## Pruebas Sugeridas

Después de cada cambio, ejecutar:
```bash
python tools/test_all_components.py
```

Y verificar:
- Forward action mean > 0.05 (al menos)
- Z-axis mean > 1.5mm (no hundir)
- Z-axis stable (no declining)
- Distance traveled > 20mm en 5 segundos

## Análisis de Movimiento de Patas

Basado en la configuración actual del CPG:

**Femur (principal para soporte vertical):**
- Offset: -0.8 rad (permanentemente flexionado)
- Stance: -0.8 + 0.15 = -0.65 rad
- Swing: -0.8 - 0.25 = -1.05 rad
- **Problema:** Nunca se extiende más allá de -0.65 rad, patas siempre dobladas

**Tibia (extensión):**
- Offset: 1.2 rad (extendido)
- Stance: 1.2 - 0.15 = 1.05 rad
- Swing: 1.2 + 0.25 = 1.45 rad
- **OK:** Está extendido, pero femur flexionado limita altura total

**Altura total estimada:**
- Femur contribución: sin(0.65) ≈ 0.6mm (muy poco)
- Tibia contribución: sin(1.05) ≈ 0.87mm
- **Total ≈ 1.47mm de altura teórica**
- Actual observado: ~0.26mm final (¡mucho peor!)

**Conclusión:** Las patas no están generando suficiente soporte vertical. La combinación de femur permanentemente flexionado y amplitude bajo cuando forward≈0 causa el hundimiento progresivo.

## Datos de Referencia

**Simulación 2026-03-12_21_11:**
- Pasos: 50,000
- Duración: 5 segundos
- Forward mean: 0.00085 (casi cero)
- Z inicial: 1.783mm
- Z final: 0.263mm (cayó 1.52mm)
- Z mean: 0.909mm (muy bajo)
- Distance traveled: 7.0mm (extremadamente poco)
- Concentración aumentó: +2.91 (la mosca está acercándose al olor, pero MUY lentamente)

**Test 2026-03-12_21_04_24 (200 pasos):**
- Forward mean: 0.016 (19x mejor)
- Z mean: 1.997mm (estable)
- Sin hundimiento observado

La diferencia sugiere que el problema es de **largo plazo** - el CPG pierde soporte vertical gradualmente cuando forward es muy bajo.
