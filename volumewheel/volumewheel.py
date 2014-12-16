#
#  volumewheel.py
#
#  Copyright: 2014 Leo Iannacone <info@leoiannacone.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#

from gi.repository import GObject, Peas, Gtk, GtkClutter, Clutter, Pango


class VolumeWheel(GObject.Object, Peas.Activatable):
    __gtype_name__ = 'VolumeWheel'

    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.new_handler_id = -1
        self.old_handler_id = -1

    def do_activate(self):
        # add the volume bar
        video = self.object.get_video_widget()
        self.volumebar = VolumeBar(self.object)
        video.get_stage().add_child(self.volumebar)
        video.get_toplevel().connect(
            "window-state-event", self.volumebar.on_state_event)
        video.get_toplevel().connect("configure-event", self.volumebar.resize)

        # block the seek event, raised with mouse scroll
        mask = GObject.SignalMatchType.ID
        event_name = "seek-requested"
        signal_id = GObject.signal_lookup(event_name, video)
        self.old_handler_id = GObject.signal_handler_find(video,
                                                          mask,
                                                          signal_id,
                                                          0, None, 0, 0)
        GObject.signal_handler_block(video, self.old_handler_id)

        # add new event handler
        self.new_handler_id = video.connect(event_name, self.wheel_handler)

    def do_deactivate(self):
        video = self.object.get_video_widget()
        GObject.signal_handler_unblock(video, self.old_handler_id)
        GObject.signal_handler_disconnect(video, self.new_handler_id)

    def wheel_handler(self, video, forward):
        step = 0.05
        if not forward:
            step = -step
        volume = self.object.get_volume() + step
        if volume < 0 or volume > 1:
            volume = int(volume)
        self.object.set_volume(volume)
        self.volumebar.set_volume(volume)

        return False


class VolumeBar (Clutter.Actor):

    MIN_WIDTH = 200
    MAX_WIDTH = 0.2

    BAR_HEIGHT = 0.6
    BAR_WIDTH = 36
    BAR_BORDER = 4
    COLOR = Clutter.Color.from_string("#ffffffff")[1]

    def __init__(self, totem):
        super().__init__()
        self.totem = totem
        self.volume = None

        text = Clutter.Text()
        text.set_color(self.COLOR)
        self.add_child(text)
        self.text = text

        canvas = Clutter.Canvas()
        canvas.connect("draw", self.draw_bar)
        bar = Clutter.Actor()
        bar.set_content(canvas)
        self.canvas = canvas
        self.add_child(bar)
        self.bar = bar

        self.has_size = False

    def set_volume(self, volume):
        self.volume = volume
        self.text.set_text("Volume {}%".format(round(volume * 100)))
        self.show()

    def show(self):
        # pre condition
        if not self.has_size:
            self.resize()

        self._check_fullscreen()

        # build the effect
        transition = Clutter.PropertyTransition()
        transition.set_property_name("opacity")
        transition.set_to(0)
        transition.set_delay(1400)
        transition.set_duration(600)
        transition.set_progress_mode(Clutter.AnimationMode.EASE_OUT_CUBIC)
        transition.set_remove_on_complete(True)

        self.remove_all_transitions()
        self.set_opacity(255)
        self.add_transition("fade-out", transition)

    def _check_fullscreen(self):
        # show bar only fullscreen
        if not self.totem.is_fullscreen():
            self.bar.hide()
        else:
            self.bar.show()
            self.canvas.invalidate()

    def on_state_event(self, *arg):
        self._check_fullscreen()
        self.resize()
        return False

    def resize(self, *arg):

        # pre condition
        if self.volume is None or self.volume < 0:
            self.has_size = False
            return False

        # stage
        stage = self.get_stage()
        stage_height = stage.get_height()
        stage_width = stage.get_width()

        # main actor
        actor_height = stage_height
        actor_width = max(stage_width * self.MAX_WIDTH, self.MIN_WIDTH)
        actor_y = 0
        actor_x = stage_width - actor_width
        self.set_position(actor_x, actor_y)
        self.set_size(actor_width, actor_height)

        # bar
        bar_height = stage_height * self.BAR_HEIGHT
        bar_x = (actor_width - self.BAR_WIDTH) / 2
        bar_y = (actor_height - bar_height) / 2
        self.bar.set_position(bar_x, bar_y)
        self.bar.set_size(self.BAR_WIDTH, bar_height)
        self.canvas.set_size(self.BAR_WIDTH, bar_height)
        self.canvas.invalidate()

        # text
        text_width = actor_width * 0.7
        font = Pango.FontDescription.from_string(self.text.get_font_name())
        font_factor = font.get_size() / self.text.get_width()
        font.set_size(font_factor * text_width)
        self.text.set_font_name(font.to_string())
        text_y = (bar_y - self.text.get_height()) / 2
        text_x = (actor_width - self.text.get_width()) / 2
        self.text.set_position(text_x, text_y)

        self.has_size = True

        return False

    def draw_bar(self, canvas, cr, width, height):
        # clear
        Clutter.cairo_clear(cr)
        cr.set_source_rgb(255, 255, 255)

        # border
        cr.set_line_width(self.BAR_BORDER)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

        # level
        bar_height = height * self.volume
        cr.rectangle(0, height - bar_height, width, bar_height)
        cr.fill()

        return True
