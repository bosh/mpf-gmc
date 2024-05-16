@tool
extends AudioStreamPlayer
class_name GMCChannel


# AudioStreamPlayer class has a bus property that is the string name
# of the AudioServer bus. This value is the GMC bus instance.
var _bus: GMCBus
var tweens: Array[Tween]

@warning_ignore("shadowed_global_identifier")
var log: GMCLogger

func _init(n: String, b: GMCBus):
	self.name = n
	self._bus = b
	self.log = b.log

func load_stream(filepath: String) -> AudioStream:
	self.stream = ResourceLoader.load(filepath, "AudioStreamOGGVorbis" if filepath.get_extension() == "ogg" else "AudioStreamSample") as AudioStream
	return self.stream


func play_with_settings(settings: Dictionary) -> AudioStream:
	if not self.stream:
		printerr("Attempting to play on channel %s with no stream. %s ", [self, settings])
		return

	self.log.debug("playing %s (%s) on %s with settings %s", [self.stream.resource_path, self.stream, self, settings])
	self.stream.set_meta("context", settings.context)
	var start_at: float = settings["start_at"] if settings.get("start_at") else 0.0
	var fade_in: float = settings["fade_in"] if settings.get("fade_in") else 0.0
	if settings.get("fade_out"):
		self.stream.set_meta("fade_out", settings.fade_out)

	if settings.get("loops"):
		# OGG and MPF use the 'loop' property, while WAV uses 'loop_mode
		if self.stream is AudioStreamWAV:
			self.stream.loop_mode = 1 if settings["loops"] != 0 else 0
		else:
			self.stream.loop = settings["loops"] != 0
		# Attach metadata to track the loops
		if settings["loops"] > 0:
			self.stream.set_meta("loops_remaining", settings["loops"])
			# AVW Disabling this during refactor
			#self.finished.connect(self._on_loop.bind(self))
	# elif start_at == -1.0:
	# 	# Map the sound start position relative to the music position
	# 	start_at = fmod(_music_loop_channel.get_playback_position(), channel.stream.get_length())

	# TODO: Support marker events
	if settings.get("events_when_started"):
		for e in settings["events_when_started"]:
			MPF.server.send_event(e)
	if settings.get("events_when_stopped"):
		# Store a reference to the callable so it can be disconnected
		var callable = self._trigger_events.bind("stopped", settings["events_when_stopped"])
		self.stream.set_meta("events_when_stopped", callable)
		self.finished.connect(callable)

	# If this is a voice or callout, duck the music
	# if settings.get("ducking"):
	# 	duck_settings = settings.ducking
	# 	duck_settings.release_timestamp = channel.stream.get_length() - duck_settings.get("release_point", default_duck.release_point)
	# 	if duck_settings.get("delay"):
	# 		duckAttackTimer.start(duck_settings.delay)
	# 	else:
	# 		self._duck_attack()

	# If the current volume is less than the target volume, e.g. this was fading out
	# but was re-played, force a quick fade to avoid jumping back to full
	if not fade_in and self.playing and self.volume_db < 0:
		fade_in = 0.5
	if not fade_in:
		# Ensure full volume in case it was tweened out previously
		self.volume_db = settings["volume"] if settings.get("volume") else 0.0
		self.play(start_at)
		return self.stream
	# Set the volume and begin playing
	if not self.playing:
		self.volume_db = -80.0
		self.play(start_at)
	var tween = self.create_tween()
	tween.tween_property(self, "volume_db", 0.0, fade_in).set_trans(Tween.TRANS_QUINT).set_ease(Tween.EASE_OUT)
	tween.finished.connect(self._on_fade_complete.bind(tween, "play"))
	self.tweens.append(tween)
	self.set_meta("tween", tween)
	return self.stream

func clear():
	if self.stream and self.stream.has_meta("loops_remaining"):
		self.finished.disconnect(self._on_loop)
		self.stream.remove_meta("loops_remaining")
	self.stop()
	self.volume_db = 0.0
	self.remove_meta("tween")
	self.remove_meta("is_stopping")
	self.stream = null


func _on_fade_complete(tween, action) -> void:
	self.tweens.erase(tween)
	# If this is a stop_all action, finish all the channels that are stopping
	# If this is a stop action, stop the channel
	if action == "stop" or action == "clear":
		self.log.debug("Fade out complete on channel %s" % self)
		self.clear()
	elif action == "play":
		self.log.debug("Fade in to %0.2f complete on channel %s", [self.volume_db, self])

func _on_loop() -> void:
	var loops_remaining = self.stream.get_meta("loops_remaining") - 1
	if loops_remaining == 0:
		self.stream.remove_meta("loops_remaining")
		self.finished.disconnect(self._on_loop)
		if self.stream is AudioStreamWAV:
			self.stream.loop_mode = 0
		else:
			self.loop = false
	else:
		self.stream.set_meta("loops_remaining", loops_remaining)

func _trigger_events(state, events) -> void:
	for e in events:
		MPF.server.send_event(e)
	self.finished.disconnect(self.stream.get_meta("events_when_%s" % state))
	self.stream.remove_meta("events_when_%s" % state)
