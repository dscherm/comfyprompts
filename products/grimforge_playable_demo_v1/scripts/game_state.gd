extends Node

# Persistent player state that survives world transitions. main.gd is a world
# router that frees and rebuilds the player on every world swap, so a fresh
# player.gd would reset its hp to MAX_HP each time (a full heal on travel).
# The player instead reads/writes its hp + death state here, so wounds carry
# across the courtyard <-> keep <-> town boundaries. reset() starts a fresh game
# at full hp — main.gd calls it once on initial boot, never on a world rebuild.

const MAX_HP := 100.0

var hp := MAX_HP
var max_hp := MAX_HP
var dead := false

func reset() -> void:
	hp = MAX_HP
	max_hp = MAX_HP
	dead = false
