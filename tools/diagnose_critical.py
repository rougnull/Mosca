"""
DIAGNÓSTICO CRÍTICO: Qué concentración recibe la mosca en su posición inicial
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from olfaction.odor_field import OdorField

print("\n" + "="*70)
print("DIAGNÓSTICO CRÍTICO: Concentración en posición inicial")
print("="*70)

# Parámetros
source = np.array([50.0, 50.0, 5.0])
initial_pos = np.array([10.0, 10.0, 5.0])
distance_to_source = np.linalg.norm(initial_pos - source)

print(f"\nGeometría:")
print(f"  Fuente: {source}")
print(f"  Posición inicial mosca: {initial_pos}")
print(f"  Distancia inicial: {distance_to_source:.2f}mm")

print(f"\nProbando diferentes SIGMA y AMPLITUDE:")
print("-"*70)

test_cases = [
    (0.5, 1.0),
    (0.5, 10.0),
    (1.0, 1.0),
    (1.0, 10.0),
    (2.0, 10.0),
    (3.0, 10.0),
    (5.0, 10.0),
    (5.0, 100.0),  # Amplitud muy alta
    (10.0, 100.0),
    (15.0, 100.0),  # Los parámetros fallidos originales
]

for sigma, amplitude in test_cases:
    odor_field = OdorField(sources=source, sigma=sigma, amplitude=amplitude)
    
    # 1. Concentración en posición inicial
    conc_at_init = odor_field.concentration_at(initial_pos)
    
    # 2. Concentración en la fuente
    conc_at_source = odor_field.concentration_at(source)
    
    # 3. Ratio
    ratio = conc_at_init / conc_at_source if conc_at_source > 0 else 0
    
    # Test con threshold típico
    thresholds_to_test = [0.001, 0.005, 0.01, 0.02, 0.05]
    above_threshold = [t for t in thresholds_to_test if conc_at_init > t]
    
    print(f"\n  sigma={sigma:5.1f}, amp={amplitude:6.1f}")
    print(f"    Conc @ init:   {conc_at_init:.8f}")
    print(f"    Conc @ source: {conc_at_source:.8f}")
    print(f"    Ratio:         {ratio:.8f}")
    print(f"    ✓ Detectado con threshold: {above_threshold if above_threshold else 'NINGUNO'}")

print("\n" + "="*70)
print("CONCLUSIÓN:")
print("="*70)
print("""
El gaussiano decae EXPONENCIALMENTE con distancia.
Para detectar algo a 56.6mm con sigma pequeño es IMPOSIBLE.

SOLUCIONES:
1. Aumentar SIGMA (pero pierde gradiente fino)
2. Aumentar AMPLITUDE (caro computacionalmente)
3. CAMBIAR POSICIÓN INICIAL (más cerca de la fuente)
4. Usar múltiples receptores/antenas con campos locales

RECOMENDACIÓN INMEDIATA:
- Usar sigma=5, amplitude=1 (como en el experimento fallido PERO)
- INICIALIZAR LA MOSCA MÁS CERCA (e.g., x=30, y=30 en lugar de x=10, y=10)
- Esto hace que el gradiente sea navegable desde el inicio
""")

# Test específico con mosca más cerca
print("\n" + "="*70)
print("TEST: Mosca posicionada más cerca (x=30, y=30)")
print("="*70)

better_initial_pos = np.array([30.0, 30.0, 5.0])
better_distance = np.linalg.norm(better_initial_pos - source)

print(f"\nNueva posición inicial: {better_initial_pos}")
print(f"Nueva distancia: {better_distance:.2f}mm")

for sigma, amplitude in [(5.0, 1.0), (3.0, 1.0), (2.0, 1.0)]:
    odor_field = OdorField(sources=source, sigma=sigma, amplitude=amplitude)
    conc = odor_field.concentration_at(better_initial_pos)
    print(f"  sigma={sigma}, amp={amplitude}: concentración = {conc:.6f}")
