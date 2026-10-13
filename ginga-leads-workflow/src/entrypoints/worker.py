"""Worker da Ginga Studio.

Registra os workflows de prospecção e começa a escutar execuções da plataforma.
"""

import asyncio
import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _resolve_run_worker():
    """Resolve run_worker com compatibilidade entre layouts do SDK."""
    for mod_name in ("mistralai.workflows.workflows", "mistralai_workflows"):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        run_worker = getattr(mod, "run_worker", None)
        if run_worker is not None:
            return run_worker
    from mistralai.workflows import run_worker  # type: ignore

    return run_worker


async def main() -> None:
    from src.workflows.ginga_leads import GingaLeadQualifier, GingaLeadRadar

    run_worker = _resolve_run_worker()
    await run_worker([GingaLeadRadar, GingaLeadQualifier])


if __name__ == "__main__":
    asyncio.run(main())
