def plural_ru(count: int, one: str, few: str, many: str) -> str:
    """Склонение по числу: 1 объявление, 2 объявления, 5 объявлений."""
    n = abs(int(count))
    mod100 = n % 100
    mod10 = n % 10
    if 11 <= mod100 <= 19:
        return many
    if mod10 == 1:
        return one
    if 2 <= mod10 <= 4:
        return few
    return many
