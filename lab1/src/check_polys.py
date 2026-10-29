from poly_utils import is_irreducible, is_primitive

POLYS = [
    ("f1: x^5 + x^2 + 1",             0b100101),
    ("f2: x^5 + x^4 + x^3 + x^2 + 1",  0b111101),
    ("f3: x^5 + 1",                    0b100001),
]

print(f"{'Многочлен':35} | {'неприводим':10} | {'примитивен':10}")
print("-" * 65)
for name, poly in POLYS:
    irr = is_irreducible(poly, 5)
    prim = is_primitive(poly, 5)
    print(f"{name:35} | {str(irr):10} | {str(prim):10}")