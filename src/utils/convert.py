def convert_eaqi_to_owm(eaqi: int | None) -> int | None:
    if eaqi is None:
        return None
    if eaqi <= 20:
        return 1
    elif eaqi <= 40:
        return 2
    elif eaqi <= 60:
        return 3
    elif eaqi <= 80:
        return 4
    return 5