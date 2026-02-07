from src.jutsu_academy.main_pygame_mixins import (
    AssetsMixin,
    AuthMixin,
    CoreMixin,
    GameplayMixin,
    LeaderboardMixin,
    PlayingMixin,
    RenderingMixin,
    RuntimeMixin,
    UISetupMixin,
)


class JutsuAcademy(
    CoreMixin,
    AssetsMixin,
    AuthMixin,
    UISetupMixin,
    GameplayMixin,
    RenderingMixin,
    LeaderboardMixin,
    PlayingMixin,
    RuntimeMixin,
):
    pass


def main():
    app = JutsuAcademy()
    app.run()
