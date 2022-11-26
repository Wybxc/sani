"""
# Sani 的层级结构

Sani 在设计上分为两个层级：**内核**（[sani.core][]）与 **用户接口**。

内核提供实现 Sani 基础功能的一套工具，对外暴露一个简单的抽象；
用户接口在内核的基础上进一步封装，提供更加用户友好和直接的使用体验。

???+ note "关于「洗脸池与下水管」"
    Sani 的这种层级设计类似于 git：一部分底层命令（plumbing）直接与文件系统交互，形成内容寻址的抽象；
    而另一部分用户友好的命令，或者叫上层命令（porcelain）基于底层提供的抽象，按照用户的需求封装为不同的功能。

    Plumbing 与 porcelain 直译过来是「管道系统」与「瓷器」（指瓷质的洗脸池一类）。大多数时候，用户只需要在洗脸池里洗漱，
    只有对于建造者而言，或者当用户想要突破普通洗脸池的限制时，才需要去了解管道系统的内幕。

# 核心概念

Sani 的核心抽象概念是 [`Filter`][sani.core.Filter] 与 [`SaniTree`][sani.core.SaniTree]。

Filter 是 **过滤器** ，负责对事件进行过滤、解析和处理。

Sani 将一次事件处理的过程描述为 **过滤器路径**：
一系列过滤器首尾相接，每个接收上一个的输出，进行处理，并将结果依次传递，
直到最后传给用户定义的处理函数——也是路径上的最后一个过滤器。

SaniTree 是一种用于组织 Filter 的数据结构。SaniTree 是一颗有向树，每条边上附加了 Filter 及其连接方式。

在 SaniTree 中，每一条从树根到树叶的路径都是一条过滤器路径。
收到事件后，Sani 会从树根开始，向下沿着每一条路径调用过滤器，如此完成所有路径的处理。

SaniTree 可以看成是一系列过滤器路径的集合。SaniTree 的构建方式，就是将过滤器路径不断附加其上。

为了加速和节省内存，SaniTree 的不同路径之间可以重用部分节点，这是其设计使然。
节点的重用导致在多条路径上，同一个过滤器的调用次数可能少于路径数。
对于非纯函数的过滤器，这可能会带来非预期的结果。鉴于此，Sani 的[核心约定][sani.core--核心约定]规定了
SaniTree 对于节点重用的具体行为，以保证这种重用是可预测的。

# 核心约定

Sani 核心对外提供一系列接口。出于性能优化或这其他的目的，核心的内部实现可能会随版本更替而改变。

为了保证核心的接口的稳定性，Sani 为核心的行为规定了一系列的约定，这些约定称为 **核心约定**。

???+ note "抽象泄漏"
    「抽象泄漏」是软件开发时，本应隐藏实现细节的抽象化不可避免地暴露出底层细节与局限性。
    Sani 核心为上层提供的接口也是一种抽象，故不可避免地会遭遇抽象泄漏。

    核心约定正是为了对抗抽象泄漏而存在的。它规定了比抽象本身稍多一些的行为，
    这样上层就可以依赖这些行为，而不必依赖于底层的内部实现。

    核心约定的详细程度要恰到好处，既不能过少以至于无法保证行为的稳定性，
    也不能过多以至于底层的变动无法下手。

以下是 Sani 的核心约定：

- [`Filter`][sani.core.Filter] 应该正确实现 `__eq__` 和 `__hash__`。一般来说，经过
  [`@dataclass(eq=True, frozen=True)` ][dataclasses.dataclass] 修饰即可。
- [`Filter`][sani.core.Filter] 的 [`filter`][sani.core.Filter.filter] 方法在调用时，
  `context` 参数会复制一份。这意味着 `filter` 方法内部对 `context` 的修改不会影响到外部。
- [`SaniTree`][sani.core.SaniTree] 中同一个节点出发的不同的边拥有不同的过滤器。
  此处的「不同」由 `__eq__` 和 `__hash__` 决定。
- [`SaniTree`][sani.core.SaniTree] 中，处理一个事件时，
  某个过滤器的最大可能调用次数为从根节点到该过滤器所在边的路径数。
  由于过滤器路径上较前的过滤器可能会把事件拦截，因此该过滤器的实际调用次数可能小于该值。
"""
from __future__ import annotations

import abc
import asyncio
import copy as cp
from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    Any,
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


class Filter(abc.ABC):
    """
    # 过滤器

    （待补充）
    """

    def __eq__(self, _: object) -> bool:
        raise NotImplementedError("Filter 必须指定有效的 __eq__ 实现！")

    def __hash__(self) -> int:
        raise NotImplementedError("Filter 必须指定有效的 __hash__ 实现！")

    @abc.abstractmethod
    async def filter(self, context: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        """（待补充）"""
        pass


class Op(Enum):
    AND = auto()
    OR = auto()
    CATCH = auto()


@final
class SaniTree:
    """
    # SaniTree

    （待补充）
    """

    ands: Dict[Filter, CowRef[SaniTree]]
    ors: Dict[Filter, CowRef[SaniTree]]
    catches: Dict[Filter, CowRef[SaniTree]]

    __slots__ = ("ands", "ors", "catches")

    def __init__(self) -> None:
        self.ands = {}
        self.ors = {}
        self.catches = {}

    def copy(self) -> SaniTree:
        """（待补充）"""
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


@dataclass(eq=True, frozen=True)
class UnitFilter(Filter):
    """单元过滤器。"""

    __slots__ = ()

    async def filter(self, _: Dict[str, Any], /) -> Optional[Dict[str, Any]]:
        return {}
