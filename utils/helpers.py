def truncate_text(text: str, max_length: int = 4096) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_user(user) -> str:
    name = user.full_name
    if user.username:
        return f"{name} (@{user.username})"
    return name
