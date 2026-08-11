"""Fixture: order processing with a possible null dereference (bug)."""


def total_for(order):
    # `order.lines` can be None for draft orders → AttributeError at runtime.
    return sum(line.amount for line in order.lines)


def confirm(order):
    order.status = "confirmed"
    return order
