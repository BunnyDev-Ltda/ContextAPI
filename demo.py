from context import Game


class BattleGame:
    def __init__(self):
        self.game = Game()
        self.name = "BattleGame - v1.0"
        self.data = {}


    def setup_elements(self):
        pass


    def setup_functions(self):
        pass


    def setup_events(self):
        pass


    def setup_binds(self):
        pass


    def setup_all(self):
        self.setup_elements()
        self.setup_functions()
        self.setup_events()
        self.setup_binds()


    def loop(self):
        self.setup_all()
        self.game.run(self.name)


if __name__ == "__main__":
    battle = BattleGame()
    battle.loop()
