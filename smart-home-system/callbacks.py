# Callback-i za senzore (automatizacija kuce)
def _on_door_button_pressed(self):
    """Automatski uključi svetlo kad se pritisne DS1"""
    # self.door_light.turn_on()
    pass

def _on_motion_started(self):
    """Automatski pali svetlo i zvuk pri pokretu"""
    # self.door_light.turn_on()
    # self.buzzer.beep(0.1, 1)
    pass

def _on_motion_stopped(self):
    """Isključi svetlo kad pokret prestane"""
    # self.door_light.turn_off()
    pass

def _on_membrane_pressed(self):
    """Neka akcija na pritisk membrane"""
    # self.buzzer.beep(0.15, 2)
    pass