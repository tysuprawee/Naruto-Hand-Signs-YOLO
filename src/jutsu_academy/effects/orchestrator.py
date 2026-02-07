from src.jutsu_academy.effects.base import BaseEffect, EffectContext


class EffectOrchestrator:
    def __init__(self):
        self.effects = {}
        self.active_effect_name = None
        self.passive_effect_names = set()

    def register(self, effect_name: str, effect: BaseEffect, passive=False):
        self.effects[effect_name] = effect
        if passive:
            self.passive_effect_names.add(effect_name)

    def on_jutsu_start(self, effect_name: str, context: EffectContext):
        self.active_effect_name = effect_name if effect_name in self.effects else None
        if self.active_effect_name:
            self.effects[self.active_effect_name].on_jutsu_start(context)

    def on_jutsu_end(self, context: EffectContext):
        if not self.active_effect_name:
            return
        effect = self.effects.get(self.active_effect_name)
        if effect:
            effect.on_jutsu_end(context)
        self.active_effect_name = None

    def update(self, context: EffectContext):
        names = set(self.passive_effect_names)
        if self.active_effect_name:
            names.add(self.active_effect_name)
        for name in names:
            effect = self.effects.get(name)
            if effect:
                effect.update(context)

    def render(self, screen, context: EffectContext):
        names = set(self.passive_effect_names)
        if self.active_effect_name:
            names.add(self.active_effect_name)
        for name in names:
            effect = self.effects.get(name)
            if effect:
                effect.render(screen, context)

    def on_sign_detected(self, sign_name: str, context: EffectContext):
        for name in self.passive_effect_names:
            effect = self.effects.get(name)
            if effect:
                effect.on_sign_detected(sign_name, context)

    def reset(self):
        self.active_effect_name = None
