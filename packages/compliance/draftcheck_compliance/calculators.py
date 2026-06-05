from __future__ import annotations


def area_percentage(part_m2: float, whole_m2: float) -> float:
    if whole_m2 <= 0:
        raise ValueError("whole_m2 must be greater than zero")
    return round((part_m2 / whole_m2) * 100, 2)


def compare_minimum(value: float, minimum: float) -> bool:
    return value >= minimum


def compare_maximum(value: float, maximum: float) -> bool:
    return value <= maximum


def garage_width_ratio(garage_width_m: float, frontage_width_m: float) -> float:
    if frontage_width_m <= 0:
        raise ValueError("frontage_width_m must be greater than zero")
    return round((garage_width_m / frontage_width_m) * 100, 2)


def boundary_wall_length_percentage(boundary_wall_length_m: float, lot_boundary_length_m: float) -> float:
    if lot_boundary_length_m <= 0:
        raise ValueError("lot_boundary_length_m must be greater than zero")
    return round((boundary_wall_length_m / lot_boundary_length_m) * 100, 2)
