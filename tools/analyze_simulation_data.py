#!/usr/bin/env python3
"""
Análisis de Simulación - Diagnóstico de Problemas
==================================================

Analiza el archivo .pkl de la simulación para diagnosticar:
1. Comportamiento del motor físico (física de MuJoCo)
2. Comportamiento de las extremidades (ángulos de joints)
3. Comportamiento del cerebro (acciones motoras)
4. Comportamiento del rendering (orientación y posición)

USO:
    python tools/analyze_simulation_data.py outputs/simulations/chemotaxis_3d/2026-03-12_16_49/simulation_trajectory_3d.pkl
    python tools/analyze_simulation_data.py outputs/simulations/physics_3d/2026-03-12_17_44/simulation_data.pkl
"""

import sys
import pickle
from pathlib import Path
import json
import io

# Try to import numpy (optional but recommended)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# If numpy is not available, create minimal mock classes to allow unpickling
if not HAS_NUMPY:
    import types
    import struct
    import array

    # Create a mock numpy module
    mock_numpy = types.ModuleType('numpy')

    class MockArray:
        """Mock numpy array that stores data as nested lists."""
        def __init__(self, shape=(), dtype=None, buffer=None, offset=0,
                    strides=None, order=None):
            if isinstance(shape, (list, tuple)):
                self.shape = tuple(shape) if shape else ()
            else:
                self.shape = ()
            self.dtype = dtype
            self._data = []
            self._raw_bytes = None

        def __array__(self):
            """Make it look like a numpy array."""
            return self

        def tolist(self):
            """Convert to list."""
            if self._data and isinstance(self._data, list):
                return self._data
            # Try to decode from raw bytes if we have them
            if self._raw_bytes and self.shape and self.dtype:
                try:
                    return self._decode_bytes_to_list()
                except:
                    pass
            return []

        def _decode_bytes_to_list(self):
            """Decode raw bytes to Python list based on dtype and shape."""
            if not self._raw_bytes or not self.shape:
                return []

            # Get dtype information
            dtype_str = str(self.dtype.name) if hasattr(self.dtype, 'name') else str(self.dtype)

            # Map numpy dtypes to struct format codes
            dtype_map = {
                'float64': 'd', 'float32': 'f',
                'int64': 'q', 'int32': 'i', 'int16': 'h', 'int8': 'b',
                'uint64': 'Q', 'uint32': 'I', 'uint16': 'H', 'uint8': 'B',
            }

            format_code = None
            for key in dtype_map:
                if key in dtype_str:
                    format_code = dtype_map[key]
                    break

            if not format_code:
                return []

            # Calculate total number of elements
            total_elements = 1
            for dim in self.shape:
                total_elements *= dim

            try:
                # Unpack the bytes
                values = struct.unpack(f'{total_elements}{format_code}', self._raw_bytes[:total_elements * struct.calcsize(format_code)])

                # Reshape to match the shape
                if len(self.shape) == 1:
                    return list(values)
                elif len(self.shape) == 2:
                    rows, cols = self.shape
                    return [list(values[i*cols:(i+1)*cols]) for i in range(rows)]
                else:
                    # For higher dimensions, just return flat list
                    return list(values)
            except:
                return []

        def __len__(self):
            if self.shape:
                return self.shape[0]
            return len(self._data) if isinstance(self._data, (list, tuple)) else 0

        def __getitem__(self, index):
            data = self.tolist()
            if isinstance(data, list) and isinstance(index, int) and index < len(data):
                return data[index]
            elif isinstance(index, slice):
                return data[index]
            return data

        def __setstate__(self, state):
            """Handle unpickling."""
            # Numpy arrays pickle with a 5-tuple state:
            # (version, shape, dtype, is_fortran, raw_data)
            if isinstance(state, tuple) and len(state) == 5:
                version, shape, dtype, is_fortran, raw_data = state
                self.shape = tuple(shape) if shape else ()
                self.dtype = dtype
                self._raw_bytes = raw_data
                # Try to decode immediately
                try:
                    self._data = self._decode_bytes_to_list()
                except:
                    self._data = []
            elif isinstance(state, dict):
                self.__dict__.update(state)
            else:
                self._data = state if state is not None else []

    class MockDType:
        """Mock numpy dtype."""
        def __init__(self, dtype_str, *args, **kwargs):
            self.name = dtype_str if isinstance(dtype_str, str) else str(dtype_str)

    # Reconstruction function for numpy arrays
    def _reconstruct(subtype, shape, dtype):
        """Reconstruct numpy array from pickle - called by pickle."""
        return MockArray(shape=shape, dtype=dtype)

    # Set up mock numpy module attributes
    mock_numpy.ndarray = MockArray
    mock_numpy.dtype = MockDType
    mock_numpy.int64 = int
    mock_numpy.int32 = int
    mock_numpy.int16 = int
    mock_numpy.int8 = int
    mock_numpy.uint64 = int
    mock_numpy.uint32 = int
    mock_numpy.uint16 = int
    mock_numpy.uint8 = int
    mock_numpy.float64 = float
    mock_numpy.float32 = float
    mock_numpy.float16 = float
    mock_numpy.bool_ = bool

    # Create mock submodules
    mock_core = types.ModuleType('numpy.core')
    mock_core._multiarray_umath = types.ModuleType('numpy.core._multiarray_umath')
    mock_core._multiarray_umath.ndarray = MockArray
    mock_core._multiarray_umath.dtype = MockDType
    mock_core._multiarray_umath._reconstruct = _reconstruct
    mock_core.multiarray = types.ModuleType('numpy.core.multiarray')
    mock_core.multiarray.ndarray = MockArray
    mock_core.multiarray.dtype = MockDType
    mock_core.multiarray._reconstruct = _reconstruct

    mock_core_new = types.ModuleType('numpy._core')
    mock_core_new.multiarray = types.ModuleType('numpy._core.multiarray')
    mock_core_new.multiarray.ndarray = MockArray
    mock_core_new.multiarray.dtype = MockDType
    mock_core_new.multiarray._reconstruct = _reconstruct

    mock_core_new._multiarray_umath = types.ModuleType('numpy._core._multiarray_umath')
    mock_core_new._multiarray_umath.ndarray = MockArray
    mock_core_new._multiarray_umath.dtype = MockDType
    mock_core_new._multiarray_umath._reconstruct = _reconstruct

    # Inject mocks into sys.modules
    sys.modules['numpy'] = mock_numpy
    sys.modules['numpy.core'] = mock_core
    sys.modules['numpy.core._multiarray_umath'] = mock_core._multiarray_umath
    sys.modules['numpy.core.multiarray'] = mock_core.multiarray
    sys.modules['numpy._core'] = mock_core_new
    sys.modules['numpy._core.multiarray'] = mock_core_new.multiarray
    sys.modules['numpy._core._multiarray_umath'] = mock_core_new._multiarray_umath

def load_pickle_safe(file_path):
    """Load pickle file safely, handling numpy arrays even without numpy installed."""
    if HAS_NUMPY:
        # If numpy is available, use standard pickle
        with open(file_path, 'rb') as f:
            return pickle.load(f)

    # Without numpy, try to load but provide helpful error if it fails
    print("⚠️  Intentando cargar archivo sin numpy...", flush=True)
    print("   (Los archivos creados con numpy requieren numpy para cargarse)\n", flush=True)

    try:
        with open(file_path, 'rb') as f:
            unpickler = pickle.Unpickler(f)
            data = unpickler.load()
            # Convert mock arrays to lists
            return _convert_mock_arrays_to_lists(data)
    except (pickle.UnpicklingError, ModuleNotFoundError, AttributeError, TypeError) as e:
        # If unpickling fails, provide a helpful error message
        print(f"❌ ERROR: No se puede cargar el archivo pickle sin numpy", flush=True)
        print(f"   Tipo de error: {type(e).__name__}", flush=True)
        print(f"\n   Este archivo contiene arrays de numpy que REQUIEREN numpy instalado.", flush=True)
        print(f"   \n   SOLUCIÓN: Instala numpy con el siguiente comando:", flush=True)
        print(f"   pip install numpy", flush=True)
        print(f"\n   Después vuelve a ejecutar este script.\n", flush=True)
        sys.exit(1)

def _convert_mock_arrays_to_lists(obj):
    """Recursively convert mock numpy arrays to lists."""
    if isinstance(obj, dict):
        return {key: _convert_mock_arrays_to_lists(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_mock_arrays_to_lists(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_mock_arrays_to_lists(item) for item in obj)
    elif not HAS_NUMPY and hasattr(obj, '_data'):
        # This is likely a mock array
        data = obj._data
        if isinstance(data, (list, tuple)):
            return [_convert_mock_arrays_to_lists(item) for item in data]
        return data
    else:
        return obj

# Helper functions for when numpy is not available
def safe_min(arr):
    """Get minimum value, works with lists or numpy arrays."""
    if HAS_NUMPY and hasattr(arr, '__array__'):
        return np.min(arr)
    return min(arr) if isinstance(arr, (list, tuple)) else arr

def safe_max(arr):
    """Get maximum value, works with lists or numpy arrays."""
    if HAS_NUMPY and hasattr(arr, '__array__'):
        return np.max(arr)
    return max(arr) if isinstance(arr, (list, tuple)) else arr

def safe_mean(arr):
    """Get mean value, works with lists or numpy arrays."""
    if HAS_NUMPY and hasattr(arr, '__array__'):
        return np.mean(arr, axis=0)
    if isinstance(arr, (list, tuple)):
        return sum(arr) / len(arr) if len(arr) > 0 else 0
    return arr

def safe_std(arr):
    """Get standard deviation, works with lists or numpy arrays."""
    if HAS_NUMPY and hasattr(arr, '__array__'):
        return np.std(arr, axis=0)
    if isinstance(arr, (list, tuple)) and len(arr) > 0:
        mean = safe_mean(arr)
        variance = sum((x - mean) ** 2 for x in arr) / len(arr)
        return variance ** 0.5
    return 0

def safe_allclose(arr, value, atol=0.01):
    """Check if all values are close to a value."""
    if HAS_NUMPY and hasattr(arr, '__array__'):
        return np.allclose(arr, value, atol=atol)
    if isinstance(arr, (list, tuple)):
        return all(abs(x - value) < atol for x in arr)
    return abs(arr - value) < atol

def safe_degrees(rad):
    """Convert radians to degrees."""
    if HAS_NUMPY:
        return np.degrees(rad)
    return rad * 180.0 / 3.14159265359

def is_numpy_array(obj):
    """Check if object is a numpy array."""
    return HAS_NUMPY and hasattr(obj, '__array__')

def analyze_pkl_file(pkl_path):
    """Analizar archivo .pkl de simulación."""
    print("="*70, flush=True)
    print("ANÁLISIS DE DATOS DE SIMULACIÓN", flush=True)
    print("="*70, flush=True)
    print(f"Archivo: {pkl_path}\n", flush=True)

    if not HAS_NUMPY:
        print("⚠️  ADVERTENCIA: numpy no está instalado", flush=True)
        print("   Algunas funciones de análisis estarán limitadas", flush=True)
        print("   Los datos numpy se convertirán a listas de Python", flush=True)
        print("   Instala numpy con: pip install numpy\n", flush=True)

    # Cargar datos usando el unpickler seguro
    print("Cargando archivo pickle...", flush=True)
    sys.stdout.flush()
    data = load_pickle_safe(pkl_path)
    print("Archivo cargado exitosamente.", flush=True)
    sys.stdout.flush()

    # Print with explicit flush and error handling for type
    try:
        data_type = type(data)
        sys.stdout.flush()
        type_name = data_type.__name__
        sys.stdout.flush()
        type_module = getattr(data_type, '__module__', 'builtins')
        sys.stdout.flush()
        print(f"Tipo de datos: {type_module}.{type_name}", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"Tipo de datos: [Error al obtener tipo: {e}]", flush=True)
        sys.stdout.flush()
        # Fallback to basic type info
        try:
            print(f"Tipo de datos (fallback): {type(data).__name__}", flush=True)
        except:
            print(f"Tipo de datos: Unknown", flush=True)

    if isinstance(data, dict):
        print(f"\nClaves en datos: {list(data.keys())[:20]}", flush=True)

        # Analizar cada clave
        for key in list(data.keys())[:5]:
            value = data[key]
            print(f"\n{key}:", flush=True)
            print(f"  Tipo: {type(value)}", flush=True)
            if hasattr(value, 'shape'):
                print(f"  Shape: {value.shape}", flush=True)
                if len(value.shape) > 0 and value.shape[0] > 0:
                    print(f"  Primeros valores: {value[:3]}", flush=True)
                    print(f"  Últimos valores: {value[-3:]}", flush=True)
            elif isinstance(value, (list, tuple)):
                print(f"  Longitud: {len(value)}", flush=True)
                if len(value) > 0:
                    print(f"  Tipo primer elemento: {type(value[0])}", flush=True)
                    if hasattr(value[0], 'shape'):
                        print(f"  Shape primer elemento: {value[0].shape}", flush=True)

        # Buscar información crítica
        print("\n" + "="*70, flush=True)
        print("ANÁLISIS DE INFORMACIÓN CRÍTICA", flush=True)
        print("="*70, flush=True)

        # 1. Posición y orientación
        if any('pos' in k.lower() for k in data.keys()):
            print("\n1. POSICIÓN:", flush=True)
            for key in data.keys():
                if 'pos' in key.lower():
                    value = data[key]
                    if hasattr(value, 'shape') and len(value.shape) > 0:
                        print(f"  {key}: shape={value.shape}", flush=True)
                        # Analizar si se hunde
                        if value.shape[-1] >= 3:  # tiene x, y, z
                            z_values = value[:, 2] if len(value.shape) == 2 else value[2]
                            if is_numpy_array(z_values) or isinstance(z_values, (list, tuple)):
                                print(f"    Z inicial: {z_values[0]:.4f}", flush=True)
                                print(f"    Z final: {z_values[-1]:.4f}", flush=True)
                                print(f"    Z mínimo: {safe_min(z_values):.4f}", flush=True)
                                print(f"    Z máximo: {safe_max(z_values):.4f}", flush=True)
                                if safe_min(z_values) < 0:
                                    print(f"    ⚠️  PROBLEMA: La mosca se hundió bajo el suelo (Z < 0)", flush=True)

        if any('orient' in k.lower() or 'heading' in k.lower() or 'quat' in k.lower() for k in data.keys()):
            print("\n2. ORIENTACIÓN:", flush=True)
            for key in data.keys():
                if any(x in key.lower() for x in ['orient', 'heading', 'quat', 'rotation']):
                    value = data[key]
                    if hasattr(value, 'shape'):
                        print(f"  {key}: shape={value.shape}", flush=True)
                        if len(value.shape) > 0 and value.shape[0] > 0:
                            print(f"    Inicial: {value[0]}", flush=True)
                            print(f"    Final: {value[-1]}", flush=True)
                            # Si es ángulo, convertir a grados
                            if value.shape[-1] == 1 or (len(value.shape) == 1):
                                initial_deg = safe_degrees(value[0] if isinstance(value[0], (int, float)) else value[0, 0])
                                final_deg = safe_degrees(value[-1] if isinstance(value[-1], (int, float)) else value[-1, 0])
                                print(f"    Inicial (grados): {initial_deg:.1f}°", flush=True)
                                print(f"    Final (grados): {final_deg:.1f}°", flush=True)
                                rotation = abs(final_deg - initial_deg)
                                if rotation > 170 and rotation < 190:
                                    print(f"    ⚠️  PROBLEMA: Rotación ~180° detectada ({rotation:.1f}°)", flush=True)

        # 3. Ángulos de joints
        if any('joint' in k.lower() or 'angle' in k.lower() for k in data.keys()):
            print("\n3. ÁNGULOS DE JOINTS:", flush=True)
            joint_keys = [k for k in data.keys() if 'joint' in k.lower() or 'angle' in k.lower()]
            print(f"  Encontrados {len(joint_keys)} joints", flush=True)
            if joint_keys:
                key = joint_keys[0]
                value = data[key]
                if hasattr(value, 'shape'):
                    print(f"  Ejemplo ({key}): shape={value.shape}", flush=True)
                    if len(value.shape) > 0 and value.shape[0] > 0:
                        print(f"    Valores iniciales: {value[0][:5] if len(value.shape) > 1 else value[:5]}", flush=True)
                        print(f"    Rango: [{safe_min(value):.4f}, {safe_max(value):.4f}]", flush=True)
                        # Verificar si están todos en 0 (patas rectas)
                        if safe_allclose(value, 0, atol=0.01):
                            print(f"    ⚠️  PROBLEMA: Todos los ángulos ~0 (patas rectas/no se mueven)", flush=True)

        # 4. Acciones motoras
        if any('action' in k.lower() or 'forward' in k.lower() or 'turn' in k.lower() for k in data.keys()):
            print("\n4. ACCIONES MOTORAS:", flush=True)
            for key in data.keys():
                if any(x in key.lower() for x in ['action', 'forward', 'turn', 'motor']):
                    value = data[key]
                    if hasattr(value, 'shape'):
                        print(f"  {key}: shape={value.shape}", flush=True)
                        if len(value.shape) > 0 and value.shape[0] > 0:
                            print(f"    Media: {safe_mean(value)}", flush=True)
                            print(f"    Std: {safe_std(value)}", flush=True)
                            # Verificar si hay movimiento
                            if safe_allclose(value, 0, atol=0.01):
                                print(f"    ⚠️  PROBLEMA: No hay acciones motoras (todo ~0)", flush=True)

        # 5. Timesteps/frames
        print("\n5. INFORMACIÓN DE TIEMPO:", flush=True)
        if 'times' in data or 'timestamps' in data or 'time' in data:
            time_key = 'times' if 'times' in data else 'timestamps' if 'timestamps' in data else 'time'
            times = data[time_key]
            if hasattr(times, '__len__'):
                print(f"  Total de frames: {len(times)}", flush=True)
                if len(times) > 1:
                    dt = times[1] - times[0] if isinstance(times[0], (int, float)) else times[1][0] - times[0][0]
                    fps_sim = 1.0 / dt if dt > 0 else 0
                    print(f"  dt entre frames: {dt:.6f}s", flush=True)
                    print(f"  FPS simulación: {fps_sim:.1f}", flush=True)
                    if fps_sim < 10:
                        print(f"    ⚠️  PROBLEMA: FPS muy bajo ({fps_sim:.1f} fps)", flush=True)

    elif isinstance(data, list):
        print(f"\nLista de {len(data)} elementos", flush=True)
        if len(data) > 0:
            print(f"Tipo primer elemento: {type(data[0])}", flush=True)
            if isinstance(data[0], dict):
                print(f"Claves primer elemento: {list(data[0].keys())[:10]}", flush=True)

    print("\n" + "="*70, flush=True)
    print("FIN DEL ANÁLISIS", flush=True)
    print("="*70, flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analyze_simulation_data.py <archivo.pkl>", flush=True)
        sys.exit(1)

    pkl_file = sys.argv[1]
    if not Path(pkl_file).exists():
        print(f"Error: Archivo no encontrado: {pkl_file}", flush=True)
        sys.exit(1)

    analyze_pkl_file(pkl_file)
