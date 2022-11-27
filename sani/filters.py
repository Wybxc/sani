from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from sani.core import Filter


@dataclass(eq=True, frozen=True)
class UnitFilter(Filter):
    """单元过滤器。

    （待补充）
    """

    __slots__ = ()

    async def filter(self, _: dict[str, Any], /) -> Optional[dict[str, Any]]:
        return {}


@dataclass(eq=True, frozen=True)
class TypeFilter(Filter):
    """类型过滤器。"""

    target_type: type

    __slots__ = ("target_type",)

    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        if isinstance(context["event"], self.target_type):
            return {}
        else:
            return None


@dataclass(eq=True, frozen=True)
class FuncFilter(Filter):
    """函数过滤器。"""

    func: Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]

    __slots__ = ("func",)

    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        return await self.func(context)


@dataclass(eq=True, frozen=True)
class LambdaFilter(Filter):
    """Lambda 过滤器。"""

    func: Callable[[Any], bool]

    __slots__ = ("func",)

    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        return {} if self.func(context) else None


@dataclass(eq=True, frozen=True)
class RaiseFilter(Filter):
    """Raise 过滤器。"""

    __slots__ = ()

    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        if "error" in context:
            raise context["error"]
        return None
