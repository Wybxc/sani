from typing import Any, Awaitable, Callable, List, Optional

from sani.core import SaniTree, UnitFilter


class Sani:
    """ """

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
