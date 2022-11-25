from __future__ import annotations

import abc
import asyncio
import copy as cp
from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
    final,
)


class Sani:
    """一个结构简单、可组合、易于拓展的事件系统。"""

    def __init__(
        self,
        tree: SaniTree,
        catch: Optional[Callable[[Exception], Awaitable[None]]] = None,
    ) -> None:
        self.tree = tree
        self.catch = catch

    async def emit(self, event: Any):
        """触发事件。"""
        caught: List[Exception] = []
        await self.tree.emit_and({"event": event}, UnitFilter(), caught)

        if self.catch:
            for err in reversed(caught):
                await self.catch(err)


class Filter(abc.ABC):
    """过滤器。"""

    def __eq__(self, _: object) -> bool:
        raise NotImplementedError("Filter 必须指定有效的 __eq__ 实现！")

    def __hash__(self) -> int:
        raise NotImplementedError("Filter 必须指定有效的 __hash__ 实现！")

    @abc.abstractmethod
    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        pass


class Op(Enum):
    AND = auto()
    OR = auto()
    CATCH = auto()


@final
class SaniTree:
    ands: Dict[Filter, CowRef[SaniTree]]
    ors: Dict[Filter, CowRef[SaniTree]]
    catches: Dict[Filter, CowRef[SaniTree]]

    __slots__ = ("ands", "ors", "catches")

    def __init__(self) -> None:
        self.ands = {}
        self.ors = {}
        self.catches = {}

    def copy(self) -> SaniTree:
        tree = SaniTree()
        tree.ands = {fl: child.copy() for fl, child in self.ands.items()}
        tree.ors = {fl: child.copy() for fl, child in self.ors.items()}
        tree.catches = {fl: child.copy() for fl, child in self.catches.items()}
        return tree

    __copy__ = copy

    def add_path(
        self, path: Iterable[Tuple[Op, Filter, Optional[SaniTree]]]
    ) -> SaniTree:
        """添加一条过滤器路径。"""
        curr = CowRef(self, True)
        for op, filter, branch in path:
            children = (
                curr.ref().ands
                if op is Op.AND
                else (curr.ref().ors if op is Op.OR else curr.ref().catches)
            )
            if filter in children:
                child = children[filter]
                curr = child.mut()
                if curr is not child:
                    children[filter] = curr
            else:
                curr = CowRef(branch, False) if branch else CowRef(SaniTree(), True)
                children[filter] = curr
        return self

    # 实现细节：
    # - ctx 隔离，向下传递时创建新的副本。
    # - emit 函数不应修改 self。
    # - emit 函数不应抛出 Exception。

    async def emit_and(
        self, ctx: Dict[str, Any], filter: Filter, caught: List[Exception], /
    ):
        """正常执行过滤器。
        非空结果以 AND 传给 and 子节点，以 OR 传给 or 子节点。
        空结果以 AND 传给 or 子节点。
        如果检测到错误，以 CATCH 传给 and/or 子节点，以 AND 传给 catch 子节点。"""
        try:
            res = await filter.filter(ctx)
            if res is not None:  # 过滤器返回非空
                ands = (
                    child.ref().emit_and(ctx | res, filter, caught)
                    for filter, child in self.ands.items()
                )
                ors = (
                    child.ref().emit_or(ctx | res, caught)
                    for child in self.ors.values()
                )
                await asyncio.gather(*ands, *ors)
            else:  # 过滤器返回空
                ors = (
                    child.ref().emit_and(ctx.copy(), filter, caught)
                    for filter, child in self.ors.items()
                )
                await asyncio.gather(*ors)

        except Exception as e:  # 出错
            caught.append(e)
            err = {"error": e}
            ands = (
                child.ref().emit_and(ctx | err, filter, caught)
                for filter, child in self.ands.items()
            )
            ors = (
                child.ref().emit_or(ctx | err, caught) for child in self.ors.values()
            )
            catches = (
                child.ref().emit_and(ctx | err, filter, caught)
                for filter, child in self.catches.items()
            )
            if await asyncio.gather(*catches):
                caught.pop()
            await asyncio.gather(*ands, *ors)

    async def emit_or(self, ctx: Dict[str, Any], caught: List[Exception], /):
        """跳过自身过滤器，直接以 AND 传给 and 子节点。"""
        ands = (
            child.ref().emit_and(ctx.copy(), filter, caught)
            for filter, child in self.ands.items()
        )
        await asyncio.gather(*ands)

    async def emit_catch(self, ctx: Dict[str, Any], caught: List[Exception], /):
        """跳过自身过滤器，以 CATCH 传给 and/or 子节点，以 AND 传给 catch 子节点。"""
        ands = (
            child.ref().emit_catch(ctx.copy(), caught) for child in self.ands.values()
        )
        ors = (
            child.ref().emit_catch(ctx.copy(), caught) for child in self.ors.values()
        )
        catches = (
            child.ref().emit_and(ctx.copy(), filter, caught)
            for filter, child in self.catches.items()
        )
        await asyncio.gather(*ands, *ors, *catches)


T = TypeVar("T")


class CowRef(Generic[T]):
    """Copy-on-Write 引用。"""

    value: T
    owned: bool

    __slots__ = ("value", "owned")

    def __init__(self, value: T, owned: bool) -> None:
        self.value = value
        self.owned = owned

    def ref(self) -> T:
        return self.value

    def mut(self) -> CowRef[T]:
        if self.owned:
            return self
        else:
            return CowRef(cp.copy(self.value), True)

    def copy(self) -> CowRef[T]:
        return CowRef(self.value, False)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CowRef):
            return self.value == cast(CowRef[T], other).value
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    __copy__ = copy


class SaniBuilder:
    path: List[Tuple[Op, Filter, Optional[SaniTree]]]

    def __init__(self):
        self.path = []

    def op(
        self, op: Op, filter: Filter, branch: Optional[SaniTree] = None
    ) -> SaniBuilder:
        self.path.append((op, filter, branch))
        return self

    def end(self, root: SaniTree) -> SaniTree:
        root.add_path(self.path)
        return root


@dataclass(eq=True, frozen=True)
class UnitFilter(Filter):
    """单元过滤器。"""

    __slots__ = ()

    async def filter(self, _: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        return {}
