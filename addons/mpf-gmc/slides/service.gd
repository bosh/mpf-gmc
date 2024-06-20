# Copyright 2021 Paradigm Tilt

extends MPFSlide

@export var highlight_color: Color


const triggers = ["service_button",
"service_switch_test_start", "service_switch_test_stop",
"service_coil_test_start", "service_coil_test_stop",
"service_light_test_start", "service_light_test_stop"]

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	MPF.server.service.connect(self._on_service)
	for trigger in triggers:
		MPF.server._send("register_trigger?event=%s" % trigger)
	focus()

func _exit_tree() -> void:
	for trigger in triggers:
		MPF.server._send("remove_trigger?event=%s" % trigger)

func focus():
	# Use call_deferred to grab focus to ensure tree stability
	$TabContainer.grab_focus.call_deferred()
	$TabContainer.set("custom_colors/font_color_fg", highlight_color)

func _on_service(payload):
	if payload.has("button"):
		self._on_button(payload)

func _on_button(payload):
	if not payload.has("button"):
		return

	var inputEvent = InputEventKey.new()
	inputEvent.pressed = true
	inputEvent.keycode = {
		"DOWN": KEY_DOWN,
		"UP": KEY_UP,
		"ENTER": KEY_ENTER,
		"ESC": KEY_ESCAPE,
		"PAGE_LEFT": KEY_PAGEUP,
		"PAGE_RIGHT": KEY_PAGEDOWN,
		"START": KEY_BACKSPACE,
	}[payload.button]
	print("Triggering %s INPUT EVENT: %s" % [payload.button, inputEvent])
	Input.parse_input_event(inputEvent)

func _input(event):
	if event is InputEventKey:
		print("service.gd handling input event")
		if $TabContainer.has_focus():
			print("Tab container has focus!")
			if event.keycode == KEY_ESCAPE:
				$TabContainer.select_previous_available()
			elif event.keycode == KEY_ENTER:
				$TabContainer.select_next_available()
			elif event.keycode == KEY_DOWN:
				self.select_page()
		elif event.keycode == KEY_BACKSPACE:
			self.focus()
			# Reset the focus settings of the child page
			var page = $TabContainer.get_child($TabContainer.current_tab)
			page.unfocus()

func select_page():
	# Last tab is always exit
	if $TabContainer.current_tab == $TabContainer.get_tab_count() - 1:
		MPF.server.send_event("service_trigger&action=service_exit")
		return
	var target = $TabContainer.get_child($TabContainer.current_tab)
	target.focus()

	$TabContainer.set("custom_colors/font_color_fg", null)
