from typing import Set

import pytest

from sani import *
from sani.filters import *


@pytest.mark.asyncio
async def test_emit():
    """测试正常的接收和过滤。"""
    ev = None

    async def endpoint(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal ev
        ev = ctx["event"]
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(str))
        .op(Op.OR, TypeFilter(int))
        .op(Op.AND, FuncFilter(endpoint))
        .end(SaniTree())
    )
    sani = Sani(tree)

    ev = None
    await sani.emit("test")
    assert ev == "test"

    ev = None
    await sani.emit(123)
    assert ev == 123

    ev = None
    await sani.emit([])
    assert ev is None


@pytest.mark.asyncio
async def test_emit2():
    """测试 or 分支的接收和过滤。"""
    ev = None

    async def endpoint(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal ev
        ev = ctx["event"]
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(str))
        .op(Op.AND, FuncFilter(endpoint))
        .end(SaniTree())
    )
    sani = Sani(tree)

    ev = None
    await sani.emit("test")
    assert ev == "test"

    ev = None
    await sani.emit(123)
    assert ev is None


@pytest.mark.asyncio
async def test_catch():
    """测试异常捕获过滤器。"""
    ev = None

    async def endpoint(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if ctx["event"] != "test":
            raise ValueError("test")
        raise RuntimeError("test")

    async def catcher(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal ev
        ev = ctx["error"]
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(str))
        .op(Op.AND, FuncFilter(endpoint))
        .op(Op.CATCH, LambdaFilter(lambda ctx: isinstance(ctx["error"], RuntimeError)))
        .op(Op.AND, FuncFilter(catcher))
        .end(SaniTree())
    )
    sani = Sani(tree)

    ev = None
    await sani.emit("test")
    assert type(ev) is RuntimeError

    ev = None
    await sani.emit(123)
    assert ev is None

    ev = None
    await sani.emit("not test")
    assert ev is None


@pytest.mark.asyncio
async def test_catch2():
    """测试异常捕获（非过滤器）。"""
    ev = None

    async def endpoint(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if ctx["event"] != "test":
            raise ValueError("test")
        raise RuntimeError("test")

    async def catcher(err: Exception):
        nonlocal ev
        ev = err
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(str))
        .op(Op.AND, FuncFilter(endpoint))
        .op(Op.CATCH, LambdaFilter(lambda ctx: isinstance(ctx["error"], ValueError)))
        .op(Op.OR, RaiseFilter())
        .end(SaniTree())
    )
    sani = Sani(tree, catch=catcher)

    ev = None
    await sani.emit("test")
    assert type(ev) is RuntimeError

    ev = None
    await sani.emit(123)
    assert ev is None


@pytest.mark.asyncio
async def test_multi_path():
    tree = SaniTree()
    flags: Set[str] = set()

    async def handle_str(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assert type(ctx["event"]) is str
        flags.add("str")
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(str))
        .op(Op.AND, FuncFilter(handle_str))
        .end(tree)
    )

    async def handle_int(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assert type(ctx["event"]) is int
        flags.add("int")
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(int))
        .op(Op.AND, FuncFilter(handle_int))
        .end(tree)
    )

    async def handle_list_or_dict(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assert type(ctx["event"]) in (list, dict)
        flags.add("list_or_dict")
        return None

    tree = (
        SaniBuilder()
        .op(Op.AND, TypeFilter(list))
        .op(Op.OR, TypeFilter(dict))
        .op(Op.AND, FuncFilter(handle_list_or_dict))
        .end(tree)
    )

    async def throw(err: Exception):
        raise err

    sani = Sani(tree, catch=throw)

    await sani.emit("test")
    assert "str" in flags

    await sani.emit(123)
    assert "int" in flags

    await sani.emit({})
    assert "list_or_dict" in flags
