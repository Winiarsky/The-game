class Hero():
    def __init__(self):
        self.position = None
        self.position_x = None
        self.position_y = None
        self.neighbors = []
    def __repr__(self):
        return f"position: {self.position}"
    def __eq__(self, other):
        return self.position == other.position
    def set_position(self, position:tuple[int,int]):
        self.position = position
        self.position_x = position[0]
        self.position_y = position[1]
    def make_move(self, action: str, connection):
        pass
    def _get_neighbors(self):
        pass
    def _light_tiles(self, connection):
        pass