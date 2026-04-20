from __future__ import annotations

from typing import Any

from sqlalchemy.sql import elements, visitors


def is_literal_value(value: Any) -> bool:
    """Check if value is a plain Python literal (not a SQL element or schema object)."""
    if isinstance(value, visitors.Visitable):
        return False
    if hasattr(value, "__clause_element__"):
        return False
    return True


def bind_with_type(element: elements.BindParameter[Any], type_: Any) -> elements.BindParameter[Any]:
    """Create a new BindParameter preserving all flags but with the given type."""
    return elements.BindParameter(
        element.key,
        element.value,
        type_=type_,
        unique=element.unique,
        expanding=element.expanding,
        literal_execute=element.literal_execute,
        isoutparam=element.isoutparam,
    )


def get_for_update_arg(select: Any) -> Any | None:
    return getattr(select, "_for_update_arg", None)


def get_limit_clause(select: Any) -> Any | None:
    return getattr(select, "_limit_clause", None)


def get_offset_clause(select: Any) -> Any | None:
    return getattr(select, "_offset_clause", None)
