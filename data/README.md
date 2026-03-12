# Directorio de Datos y Documentación

Este directorio contiene todos los datos, documentación técnica y notebooks del proyecto.

## Estructura

```
data/
├── docs/                          # 📚 Documentación técnica
│   ├── README.md                  # Guía de documentación
│   ├── EXECUTIVE_SUMMARY.md       # Resumen ejecutivo
│   ├── COMPLETE_CODE_REVIEW.md    # Análisis técnico completo
│   ├── WORKFLOW_GUIDE.md          # Guía de uso
│   └── SUMMARY_OF_CHANGES.md      # Historial de cambios
│
├── notebooks/                     # 📓 Jupyter Notebooks
│   ├── 0_colab_template.ipynb     # Template para Google Colab
│   ├── 1_getting_started.ipynb    # Introducción al proyecto
│   ├── 2_kinematic_replay.ipynb   # Replay cinemático
│   ├── 3_fly_following.ipynb      # Seguimiento de mosca
│   ├── 2d-3d/                     # Notebooks de visualización 2D-3D
│   └── extra/                     # Notebooks adicionales
│
└── inverse_kinematics/            # 🔧 Datos de cinemática inversa
```

## Contenido por Subdirectorio

### 📚 docs/
Contiene toda la documentación técnica del proyecto:
- Análisis de código
- Guías de uso
- Resúmenes ejecutivos
- Historial de cambios

**Ver**: `docs/README.md` para detalles completos

### 📓 notebooks/
Jupyter notebooks interactivos para:
- Aprender a usar el sistema
- Visualizar resultados
- Experimentar con parámetros
- Análisis de datos

**Cómo usar**:
```bash
# Desde la raíz del proyecto
jupyter notebook data/notebooks/
```

### 🔧 inverse_kinematics/
Datos de cinemática inversa para el modelo de Drosophila.

---

## Inicio Rápido

### Para documentación técnica:
```bash
# Ver guía de workflow
cat data/docs/WORKFLOW_GUIDE.md

# Ver resumen ejecutivo
cat data/docs/EXECUTIVE_SUMMARY.md
```

### Para notebooks interactivos:
```bash
# Abrir notebook de introducción
jupyter notebook data/notebooks/1_getting_started.ipynb
```

---

**Última actualización**: 2026-03-12
