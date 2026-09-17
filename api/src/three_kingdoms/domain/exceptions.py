class CharacterNotFound(Exception):
    """Exception raised when a character's key is not found."""

    def __init__(self, character_id: str):
        self.message = f"Character for {character_id} not found."
        super().__init__(self.message)


class CharacterContextNotFound(Exception):
    """Exception raised when a character's context is not found."""

    def __init__(self, character_id: str):
        self.message = f"Character context for {character_id} not found."
        super().__init__(self.message)
