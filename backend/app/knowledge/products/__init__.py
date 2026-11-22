"""Registry of the three product knowledge bases (and only these three)."""

from ..schema import ProductKB
from .cashmere import KB as CASHMERE
from .duck_down import KB as DUCK_DOWN
from .sheep_wool import KB as SHEEP_WOOL

PRODUCTS: dict[str, ProductKB] = {
    kb.id: kb for kb in (SHEEP_WOOL, DUCK_DOWN, CASHMERE)
}


def get_kb(product_id: str) -> ProductKB:
    try:
        return PRODUCTS[product_id]
    except KeyError:
        raise ValueError(
            f"Unsupported product {product_id!r}. Choose one of: {', '.join(PRODUCTS)}."
        ) from None
