from typing import Dict, Any, List, Union
from dataclasses import dataclass, field

@dataclass
class ParameterDefinition:
    name: str
    param_type: str  # "float", "int", "str", "bool"
    allowed_values: List[Any]
    default: Any
    source: str
    description: str

class ParameterSpace:
    """
    Generic parameter-space abstraction for YarTrader research optimization.
    Discovers allowed strategy/risk parameters without mutating Trading Core defaults.
    """
    def __init__(self, parameters: Dict[str, List[Any]] = None) -> None:
        self._definitions: Dict[str, ParameterDefinition] = {}
        if parameters:
            for name, vals in parameters.items():
                self.add_parameter(
                    name=name,
                    param_type="float" if isinstance(vals[0], float) else ("int" if isinstance(vals[0], int) else "str"),
                    allowed_values=vals,
                    default=vals[0],
                    source="ResearchParameterSpace",
                    description=f"Research parameter for {name}"
                )

    def add_parameter(
        self,
        name: str,
        param_type: str,
        allowed_values: List[Any],
        default: Any,
        source: str,
        description: str
    ) -> None:
        self._definitions[name] = ParameterDefinition(
            name=name,
            param_type=param_type,
            allowed_values=allowed_values,
            default=default,
            source=source,
            description=description
        )

    def get_parameter(self, name: str) -> ParameterDefinition:
        return self._definitions.get(name)

    def list_parameters(self) -> List[str]:
        return list(self._definitions.keys())

    def generate_cartesian_product(self) -> List[Dict[str, Any]]:
        """
        Generates deterministic Cartesian product of all parameter combinations.
        """
        import itertools
        if not self._definitions:
            return [{}]

        keys = list(self._definitions.keys())
        value_lists = [self._definitions[k].allowed_values for k in keys]

        combinations = []
        for combo in itertools.product(*value_lists):
            combinations.append(dict(zip(keys, combo)))

        return combinations
