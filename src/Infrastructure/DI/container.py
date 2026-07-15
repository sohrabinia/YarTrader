import threading
from typing import Any, Callable, Dict, Type, TypeVar, Union

T = TypeVar("T")

class DIContainer:
    """A lightweight, thread-safe Dependency Injection (DI) container supporting Singletons and Transients."""
    def __init__(self) -> None:
        self._registrations: Dict[Type, Callable[[], Any]] = {}
        self._singletons_registry: Dict[Type, bool] = {}
        self._singleton_instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()

    def register_singleton(self, interface: Type[T], factory: Union[Type[T], Callable[[], T]]) -> None:
        """Registers a service as a singleton."""
        with self._lock:
            if callable(factory) and not isinstance(factory, type):
                self._registrations[interface] = factory
            else:
                self._registrations[interface] = lambda: factory()
            self._singletons_registry[interface] = True
            if interface in self._singleton_instances:
                del self._singleton_instances[interface]

    def register_transient(self, interface: Type[T], factory: Union[Type[T], Callable[[], T]]) -> None:
        """Registers a service as a transient (new instance created on each resolve)."""
        with self._lock:
            if callable(factory) and not isinstance(factory, type):
                self._registrations[interface] = factory
            else:
                self._registrations[interface] = lambda: factory()
            self._singletons_registry[interface] = False

    def resolve(self, interface: Type[T]) -> T:
        """Resolves a registered service interface."""
        with self._lock:
            if interface not in self._registrations:
                if isinstance(interface, type):
                    try:
                        return interface()
                    except Exception as e:
                        raise ValueError(f"Dependency Injection Error: Concrete type '{interface}' could not be automatically resolved: {str(e)}")
                raise ValueError(f"Dependency Injection Error: Type '{interface}' is not registered in the DI container.")

            # Check singleton
            if self._singletons_registry.get(interface, False):
                if interface not in self._singleton_instances:
                    self._singleton_instances[interface] = self._registrations[interface]()
                return self._singleton_instances[interface]

            # Transient
            return self._registrations[interface]()

    def clear(self) -> None:
        """Clears all registrations and singleton cache."""
        with self._lock:
            self._registrations.clear()
            self._singletons_registry.clear()
            self._singleton_instances.clear()

# Global instance
container_instance = DIContainer()
