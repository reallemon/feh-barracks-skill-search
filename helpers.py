def get_english_name(unit_id: str, translation_map: dict[str, str]) -> str:
    """
    Constructs the full English name for a unit ID.
    Handles honorifics (MPID_HONOR) if present.
    """
    base_name: str = translation_map.get("M" + unit_id, unit_id)

    if "PID_" in unit_id:
        honor_key: str = unit_id.replace("PID", "MPID_HONOR")
        if honor_key in translation_map:
            base_name += f": {translation_map[honor_key]}"

    return base_name
