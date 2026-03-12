# Arquitectura Modular de Renderizado 3D - NeuroMechFly Sim

**Versión**: 2.0 (Refactoring Modular)  
**Fecha**: 2026-03-12  
**Estado**: ✅ IMPLEMENTADO

## Motivación

El renderizador anterior era una clase monolítica (`MuJoCoRenderer`) que hacía todo:
- Cargar datos
- Configurar FlyGym  
- Renderizar frames
- Guardar video

**Problemas**:
- Difícil de testear (todas las responsabilidades acopladas)
- Difícil de depurar (errores en un paso afectan todo el pipeline)
- No reutilizable (si solo querías cargar datos o setup, tenías que arrastrar todo)
- Difícil de mantener (cambios en un paso requieren entender todo)

## Nueva Arquitectura: Modular por Responsabilidad

```
                     ┌─────────────────────────────────┐
                     │    RenderingPipeline (MAIN)      │
                     │   (orchestrator del flujo)       │
                     └─────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
          ┌─────────┐   ┌────────────┐  ┌──────────┐
          │ DataLoader  │EnvironSetup│  │FrameRend │
          └─────────┘   │   (Setup)  │  │ (Render) │
              ↓         └────────────┘  └──────────┘
          extract                           │
          joints                            ▼
              │                         ┌──────────┐
              │                         │VideoWrit │
              └─────────────────────────┤  (Save)  │
                    joint_angles        └──────────┘
                                            │
                                            ▼
                                        fly_3d.mp4
```

## Módulos

### 1. DataLoader (`data_loader.py`)

**Responsabilidad**: Cargar y preparar datos cinemáticos

```python
from src.rendering import DataLoader

loader = DataLoader(verbose=True)
loader.load_from_file("simulations/sim_001/data.pkl")
loader.extract_joint_angles()
is_valid, msg = loader.validate_data_integrity()
joint_angles = loader.get_joint_angles()  # Dict[joint_name, angle_array]
n_frames = loader.get_n_frames()
```

**Métodos**:
- `load_from_file(data_file)`: Cargar .pkl
- `extract_joint_angles()`: Extraer ángulos
- `validate_data_integrity()`: Validar datos
- `get_joint_angles()`: Obtener dict de angles
- `get_n_frames()`: Obtener número de frames

**Flujo esperado**:
```
File (.pkl) → load → extract → validate → Dict[joint, angles]
```

### 2. EnvironmentSetup (`environment_setup.py`)

**Responsabilidad**: Configurar FlyGym para renderizado

```python
from src.rendering import EnvironmentSetup

setup = EnvironmentSetup(verbose=True)
setup.setup_complete(
    arena_type="flat",
    camera_type="yaw_only"
)
sim = setup.get_simulation()
```

**Métodos**:
- `setup_fly()`: Inicializar Fly model
- `setup_arena(arena_type)`: Configurar arena
- `setup_simulation()`: Crear SingleFlySimulation
- `setup_camera(camera_type)`: Configurar cámara
- `setup_complete(**kwargs)`: Hacer todo en orden

**Flujo esperado**:
```
FlyGym Init → Fly + Arena → Simulation + Camera → Ready to step
```

**Tipos soportados**:
- Arena: "flat", "terrain" (futura)
- Camera: "yaw_only", "fixed" (futura)

### 3. FrameRenderer (`frame_renderer.py`)

**Responsabilidad**: Renderizar frames desde datos cinemáticos

```python
from src.rendering import FrameRenderer

renderer = FrameRenderer(
    simulation=sim,
    joint_angles=joint_angles,
    verbose=True
)
renderer.render_frames(fps=60)
frames = renderer.get_frames()
```

**Métodos**:
- `render_frames(fps)`: Renderizar todos los frames
- `get_frames()`: Obtener lista de frames
- `get_frame_count()`: Número de frames exitosos
- `get_error_count()`: Número de frames con error
- `get_error_indices()`: Índices de frames fallidos

**Flujo esperado**:
```
For each frame:
  1. Extract joint angles for frame i
  2. Call simulation.step(action)
  3. Capture frame from MuJoCo
  4. Append to frames list
```

**Manejo de errores**:
- Si un frame falla, lo registra pero continúa
- Permite video con algunos frames saltados
- Reporte final muestra frames con error

### 4. VideoWriter (`video_writer.py`)

**Responsabilidad**: Guardar frames como video MP4

```python
from src.rendering import VideoWriter

writer = VideoWriter(verbose=True)
writer.save_video(
    frames=frames,
    output_path="output/fly_3d.mp4",
    fps=60,
    quality=5  # 1-31, menor=mejor
)
info = writer.get_last_output_info()
```

**Métodos**:
- `save_video(frames, output_path, fps, quality, codec)`: Guardar MP4
- `validate_frames(frames)`: Validar frames antes de guardar
- `get_last_output_info()`: Metadata del último video

**Características**:
- Soporta MP4, AVI, GIF, MOV
- Validación de frames antes de guardar
- Información de tamaño y duración
- Manejo de pixel formats (yuv420p para MP4)

### 5. RenderingPipeline (`rendering_pipeline.py`)

**Responsabilidad**: Orquestar el flujo completo

```python
from src.rendering import RenderingPipeline

pipeline = RenderingPipeline(verbose=True)
success = pipeline.render(
    data_file="simulations/sim_001/data.pkl",
    output_video="outputs/sim_001.mp4",
    fps=60,
    arena_type="flat",
    camera_type="yaw_only",
)

report = pipeline.get_report()
pipeline.save_report("report.json")
```

**Flujo**:
```
[1/4] Load Data → [2/4] Setup Env → [3/4] Render → [4/4] Save Video
```

**Reporte JSON**:
```json
{
  "status": "success",
  "components": {...},
  "data": {
    "input_file": "...",
    "output_file": "...",
    "fps": 60
  },
  "results": {
    "total_frames": 1200,
    "error_frames": 0,
    "video_info": {
      "path": "...",
      "frames": 1200,
      "duration_seconds": 20.0,
      "size_mb": 45.2
    }
  }
}
```

## Casos de Uso

### Caso 1: Render Completo (Recomendado)

Usar `RenderingPipeline` para todo en uno:

```python
from src.rendering import RenderingPipeline

pipeline = RenderingPipeline()
pipeline.render(
    data_file="simulations/sim_001/data.pkl",
    output_video="outputs/media/fly_3d.mp4",
    fps=60,
)
```

**Ventajas**: Simple, reportes automáticos, manejo de errores integrado.

### Caso 2: Componentes Individuales

Usar módulos solo cuando necesites flexibilidad:

```python
from src.rendering import (
    DataLoader, EnvironmentSetup, 
    FrameRenderer, VideoWriter
)

# Cargar datos
loader = DataLoader()
loader.load_from_file("data.pkl")
loader.extract_joint_angles()
joints = loader.get_joint_angles()

# Setup personalizado
setup = EnvironmentSetup()
setup.setup_fly()
setup.setup_arena()
setup.setup_simulation()
# ... configuración extra aquí ...
setup.setup_camera()

# Renderizar
renderer = FrameRenderer(setup.get_simulation(), joints)
renderer.render_frames(fps=60)

# Guardar con opciones
writer = VideoWriter()
writer.save_video(
    renderer.get_frames(),
    "output.mp4",
    fps=60,
    quality=3  # HIGH QUALITY
)
```

**Ventajas**: Control total, debugging granular.

### Caso 3: Renderizar Trayectorias Existentes

Script que renderiza todos los archivos .pkl en un directorio:

```python
from pathlib import Path
from src.rendering import RenderingPipeline

data_dir = Path("simulations/batch_001")
for pkl_file in data_dir.glob("*/data.pkl"):
    sim_name = pkl_file.parent.name
    output_file = f"outputs/{sim_name}_3d.mp4"
    
    pipeline = RenderingPipeline(verbose=False)
    pipeline.render(pkl_file, output_file, fps=60)
    
    report = pipeline.get_report()
    print(f"{sim_name}: {report['status']}")
```

## Integración con Workflow

El `SimulationWorkflow` en `/src/workflow/` ahora usa `RenderingPipeline`:

```python
from src.workflow import SimulationWorkflow
from src.rendering import RenderingPipeline

workflow = SimulationWorkflow()
success = workflow.run(odor_field, brain, duration=10.0)

if success:
    # Renderizar automáticamente
    pipeline = RenderingPipeline()
    pipeline.render(
        data_file=workflow.get_output_data_file(),
        output_video=workflow.get_output_dir() / "3d_animation.mp4"
    )
```

## Manejo de Errores

### DataLoader
- ✓ Valida existencia de archivo
- ✓ Detecta formato inválido
- ✓ Verifica integridad de datos (NaN, Inf)
- ✓ Valida consistencia entre joints

### EnvironmentSetup
- ✓ Verifica disponibilidad de FlyGym
- ✓ Captura errores en cada paso
- ✓ Permite inspection de componentes parciales
- ✓ Fallback a configuración default

### FrameRenderer
- ✓ Maneja errores por frame individually
- ✓ Continúa con siguientes frames si uno falla
- ✓ Reporta índices de frames fallidos
- ✓ Valida número mínimo de frames

### VideoWriter
- ✓ Valida tipo y forma de frames
- ✓ Verifica espacio disponible
- ✓ Crea directorio destino si no existe
- ✓ Maneja diferentes formatos de video

### RenderingPipeline
- ✓ Detiene pipeline en primer error crítico
- ✓ Genera reporte detallado
- ✓ Permite guardar reporte en JSON
- ✓ Log completo de ejecución

## Prueba de Arquitectura

La arquitectura se puede probar con:

```bash
cd "C:\Users\eduar\Documents\Workspace\NeuroMechFly Sim"
.venv\Scripts\python.exe -c "
from src.rendering import RenderingPipeline
from pathlib import Path

pipeline = RenderingPipeline(verbose=True)
# Encontrar primer .pkl en simulations/
pkl_files = list(Path('simulations').glob('*/data.pkl'))
if pkl_files:
    pipeline.render(pkl_files[0])
else:
    print('No .pkl files found')
"
```

## Próximos Pasos

### Mejoras Planeadas
- [ ] Soporte para múltiples cámaras simultáneamente
- [ ] Exporta a múltiples formatos (GIF, WebP) de una sola ejecución
- [ ] GPU acceleration para rendering (si FlyGym lo soporta)
- [ ] Custom camera paths y keyframes
- [ ] Overlay de datos (scores, heatmaps, etc.)

### Extensiones
- [ ] `debug_renderer.py`: Renderizar frames individuales para debugging
- [ ] `batch_renderer.py`: Renderizar múltiples simulaciones en paralelo
- [ ] `comparison_viewer.py`: Comparar videos lado a lado
- [ ] `performance_monitor.py`: Monitor de FPS y resources durante render

## Changelog Arquitectura

### v2.0 (2026-03-12)
- ✅ Refactoring: Monolítica → Modular
- ✅ Separación: 5 módulos independientes
- ✅ Mejorado: Manejo de errores granular
- ✅ Mejorado: Reportes y debugging
- ✅ Mejorado: Reutilizabilidad de módulos
- ✅ Documentado: Casos de uso con ejemplos

### v1.0 (anterior)
- ⚠️ Monolítica: Una clase `MuJoCoRenderer` que hacía todo
- ⚠️ Acoplado: Cambios en un aspecto afectaban todo
- ⚠️ Limitado: No permitía uso granular de componentes

## Compatibilidad

**Compatibilidad hacia atrás**: 
- ✓ `MuJoCoRenderer` se mantiene en `/src/rendering/mujoco_renderer.py`
- ✓ Importable desde `src.rendering` para compatibilidad
- ⚠️ Pero se recomienda migrar a `RenderingPipeline`

## Referencias

- **FlyGym API**: https://github.com/NeLy-EPFL/flygym
- **MuJoCo Rendering**: FlyGym internals, SingleFlySimulation
- **Video Encoding**: imageio, libx264 codec
