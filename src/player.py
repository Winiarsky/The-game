from hero import Hero
class Player():
    def __init__(self, player_id: str):
        self.player_id = player_id
        self.hero = None
    
    def __hash__(self):
        return hash(self.player_id)
    
    def __repr__(self):
        return f"Player({self.player_id})"

    def assign_hero(self, hero: Hero):
        self.hero = hero