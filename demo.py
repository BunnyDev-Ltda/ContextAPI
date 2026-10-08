from context import Game



class BattleGame:
    def __init__(self):
        self.game = Game()
        self.name = "BattleGame - v1.0"
        self.data = {}


    def setup_elements(self):
        self.main = self.game.context.create_rect(
            "main_window",
            size=(self.game.w-50, self.game.h-50),
            pos=(25, 25),
            color=(255, 255, 255),
            border=4,
            show=True
        )

        self.game_title = self.game.context.create_text(
            "game_title",
            content="RPG",
            anchor=self.main,
            align="relative.mid.top",
            fsize=30,
            adjust=(0, 5),
            color=(255, 255, 255)
        )


        self.status_window = self.game.context.create_rect(
            "status_window",
            anchor=self.main,
            size=self.main.ui.get_half((1, 3), (-32, 0)),
            align="relative.bottomleft",
            adjust=(16, -16),
            color=(50, 50, 100),
            bcolor=(154, 168, 187),
            bsize=4
        )

        self.status_space = self.game.context.create_line(
            "status_space",
            anchor=self.status_window,
            align="relative.mid.top",
            border=4,
            color=(154, 168, 187),
            stadjust=(-1, 0),
            eadjust=(-1, -1)
        )

        self.player_status = self.game.context.create_text(
            "player_status",
            content="Nome: Player\nVida: 100/100",
            fsize=12,
            color=(20, 220, 20),
            anchor=self.status_window,
            align="relative.mid.topleft",
            adjust=(10, 10)
        )

        self.modal_teste = self.game.context.create_modal(
            "modal_teste",
            pos=(200, 100),
            size=(275, 225),
            bsize=3,
            tsize=15,
            color=(40, 40, 60),
            bcolor=(0, 200, 255),
            tshow=True
        )

        self.button_teste = self.game.context.create_button(
            "button_teste",
            size=(150, 40),
            anchor=self.modal_teste,
            align="relative.topleft",
            adjust=(15, 15),
            color=(70, 70, 90),
            hcolor=(100, 100, 130),
            bsize=2,
            bcolor=(200, 200, 200),
            hstep=20,
            on_click=lambda: print("Click!")
        )

        self.button_label = self.game.context.create_text(
            "button_label",
            content="Hello World!",
            anchor=self.button_teste,
            align="relative.mid.center",
            fsize=18,
            color=(255, 255, 255)
        )

        self.image_teste = self.game.context.create_image(
            "image_teste",
            pos=(200, 200),
            path="du_bist_gut_genug.png",
            size=(300, 300)
        )

    def setup_functions(self):
        pass


    def setup_events(self):
        self.image_teste.ui.movement.setup_movset()


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
