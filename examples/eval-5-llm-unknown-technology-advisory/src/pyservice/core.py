def total_price(unit_price: float, quantity: int, tax_rate: float) -> float:
    """Return the total price including tax."""
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    subtotal = unit_price * quantity
    return round(subtotal * (1 + tax_rate), 2)
