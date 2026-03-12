"""
Módulo de modelado del campo de olor.

Define clases para generar campos de gradiente olfativo basados en
distribuciones gaussianas 3D, permitiendo simulación de quimiotaxis.
"""

import numpy as np
from typing import Union, Tuple, List


class OdorField:
    """
    Modelo de campo de olor con una o múltiples fuentes gaussianas.
    
    La concentración en cualquier punto se calcula como la suma de gaussianas
    3D centradas en las posiciones de las fuentes. Simula la dispersión
    turbulenta de un odorante en el aire.
    
    Parameters
    ----------
    sources : Tuple[float, float, float] or List[Tuple[float, float, float]]
        Posición(es) de la(s) fuente(s) de olor en coordenadas (x, y, z).
        Si es una tupla simple, define una única fuente.
        Si es una lista, múltiples fuentes.
    sigma : float, default=1.0
        Desviación estándar (ancho) de la gaussiana. Simula la difusión
        del olor. Valores pequeños = gradiente más pronunciado.
    amplitude : float, default=1.0
        Amplitud máxima de la concentración en la fuente.
    """
    
    def __init__(
        self,
        sources: Union[Tuple[float, float, float], List[Tuple[float, float, float]]] = (0, 0, 0),
        sigma: float = 1.0,
        amplitude: float = 1.0
    ):
        """Inicializar el campo de olor."""
        sources = np.asarray(sources, dtype=float)
        
        # Ensure sources is 2D: (M, 3)
        if sources.ndim == 1:
            # Single source [x, y, z] -> [[x, y, z]]
            self.sources = sources[np.newaxis, :]
        elif sources.ndim == 2:
            # Multiple sources [[x1,y1,z1], [x2,y2,z2], ...]
            self.sources = sources
        else:
            raise ValueError(f"sources must be 1D or 2D array, got shape {sources.shape}")
        
        self.sigma = sigma
        self.amplitude = amplitude
    
    def concentration_at(self, position: np.ndarray) -> float:
        """
        Calcular la concentración de olor en una posición dada.
        
        Parameters
        ----------
        position : np.ndarray
            Posición (x, y, z) donde se evalúa la concentración.
            Shape puede ser (3,) o (N, 3) para múltiples posiciones.
        
        Returns
        -------
        float or np.ndarray
            Concentración (0 a amplitude). Si position es (3,), retorna float.
            Si es (N, 3), retorna array de shape (N,).
        """
        position = np.asarray(position)
        original_shape = position.shape
        
        # Asegurar que position sea 2D: (N, 3)
        if position.ndim == 1:
            position = position[np.newaxis, :]
            squeeze_output = True
        else:
            squeeze_output = False
        
        # Calcular distancia euclidiana a todas las fuentes
        # position shape: (N, 3)
        # sources shape: (M, 3)
        # diff shape: (N, M, 3)
        diff = position[:, np.newaxis, :] - self.sources[np.newaxis, :, :]
        distances_sq = np.sum(diff**2, axis=2)  # (N, M)
        
        # Gaussiana: exp(-d^2 / (2*sigma^2))
        # max_concentration shape: (N, M)
        max_concentration = self.amplitude * np.exp(-distances_sq / (2 * self.sigma**2))
        
        # Sumar contribuciones de todas las fuentes
        concentration = np.sum(max_concentration, axis=1)  # (N,)
        
        if squeeze_output:
            concentration = concentration[0]
        
        return concentration
    
    def concentration_at_multiple(self, positions: np.ndarray) -> np.ndarray:
        """
        Versión explícita para evaluar en múltiples posiciones.
        
        Parameters
        ----------
        positions : np.ndarray
            Array de shape (N, 3) con N posiciones.
        
        Returns
        -------
        np.ndarray
            Array de concentraciones shape (N,).
        """
        return self.concentration_at(positions)
    
    def gradient_at(self, position: np.ndarray, delta: float = 0.001) -> np.ndarray:
        """
        Calcular el gradiente de concentración (∇c) usando diferencias finitas.
        
        Útil para navegación quimiotáctica basada en gradientes.
        
        Parameters
        ----------
        position : np.ndarray
            Posición (x, y, z) donde se evalúa el gradiente.
        delta : float, default=0.001
            Tamaño del paso para diferencias finitas.
        
        Returns
        -------
        np.ndarray
            Gradiente [∂c/∂x, ∂c/∂y, ∂c/∂z].
        """
        position = np.asarray(position, dtype=float)
        gradient = np.zeros(3)
        
        c_center = self.concentration_at(position)
        
        for i in range(3):
            pos_plus = position.copy()
            pos_plus[i] += delta
            c_plus = self.concentration_at(pos_plus)
            gradient[i] = (c_plus - c_center) / delta
        
        return gradient
    
    def update_sources(self, new_sources: Union[Tuple, List]):
        """Actualizar las posiciones de las fuentes (ej. para dinámicas)."""
        if isinstance(new_sources[0], (int, float)):
            self.sources = np.array([new_sources])
        else:
            self.sources = np.array(new_sources)


def test_odor_field():
    """Test básico del campo de olor."""
    # Una única fuente en el origen
    field = OdorField(sources=(0, 0, 0), sigma=1.0, amplitude=1.0)
    
    # La concentración máxima debe estar en la fuente
    c_at_source = field.concentration_at(np.array([0, 0, 0]))
    assert np.isclose(c_at_source, 1.0), f"Expected 1.0, got {c_at_source}"
    
    # La concentración disminuye con la distancia
    c_at_1unit = field.concentration_at(np.array([1, 0, 0]))
    assert c_at_1unit < c_at_source, "Concentration should decrease with distance"
    
    # Test con múltiples posiciones
    positions = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    concentrations = field.concentration_at(positions)
    assert concentrations.shape == (3,), f"Expected shape (3,), got {concentrations.shape}"
    assert np.all(np.diff(concentrations) <= 0), "Concentrations should decrease monotonically"
    
    # Test con múltiples fuentes
    field_multi = OdorField(
        sources=[(0, 0, 0), (5, 0, 0)],
        sigma=1.0,
        amplitude=1.0
    )
    c_between = field_multi.concentration_at(np.array([2.5, 0, 0]))
    assert c_between > 0, "Concentration between two sources should be positive"
    
    # Test gradiente
    gradient = field.gradient_at(np.array([0.5, 0, 0]))
    assert gradient.shape == (3,), "Gradient should have shape (3,)"
    
    print("✓ Todas las pruebas de OdorField pasaron.")


if __name__ == "__main__":
    test_odor_field()
