from collections.abc import Iterable
from contextlib import contextmanager
import os
import gi
import logging
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

from itertools import tee


class Pipeline:
    """
    Pythonic wrapper to Gst.Pipeline
    """
    def __init__(self, loop: GLib.MainLoop, name: str | None = None):
        self.loop = loop
        self.pipeline = Gst.Pipeline(name)
        if not self.pipeline:
            raise RuntimeError("Unable to create pipeline.")

        self.logger = logging.getLogger(repr(self))
        self._setup_bus()
    
    def __repr__(self):
        return f'{self.__class__.__name__}("{self.pipeline.name}")'
    
    def _setup_bus(self):
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message, self.loop)
    
    def on_message(self, bus, message, loop):
        if message.type == Gst.MessageType.EOS:
            self.logger.info("End-of-stream")
            loop.quit()

        elif message.type == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            self.logger.warning(f"Warning: {err}: {debug}")

        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Error: {err}: {debug}")
            loop.quit()

        return True

    def make(self, factory: str, name: str | None = None, /, properties: dict | None = None):
        elem = Gst.ElementFactory.make(factory, name)
        if not elem:
            raise RuntimeError(f"Could not create element '{factory}'")
        
        if properties:
            for key, item in properties.items():
                elem.set_property(key, item)

        self.pipeline.add(elem)
        return elem
    
    def __getitem__(self, name: str):
        return self.pipeline.get_by_name(name)
    
    def link(self, names_or_elems: Iterable[str | Gst.Element]):
        elems = (self[elem] if isinstance(elem, str) else elem for elem in names_or_elems)
        elems_a, elems_b = tee(elems)
        next(elems_b)
        for elem_a, elem_b in zip(elems_a, elems_b):
            success = elem_a.link(elem_b)
            if not success:
                raise RuntimeError(f"Failed to link {elem_a.name} → {elem_b.name}")
    
    def set_state(self, state: Gst.State):
        self.logger.info(f"Setting {self} state to {state}")
        ret = self.pipeline.set_state(state)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Unable to set {self} to {state} state")

    def first_start(self):
        # Start pipeline in PAUSED state to allow dynamic pad connections to complete
        self.set_state(Gst.State.PAUSED)
        
        # Wait for state change to complete
        ret = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        if ret[0] == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("Failed to reach PAUSED state")
        
        self.set_state(Gst.State.PLAYING)
    
    @contextmanager
    def push_state(self, state):
        _, previous_state, _ = self.pipeline.get_state(0)

        result = self.pipeline.set_state(state)
        if result == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Failed to set pipeline state to {state!r}")

        try:
            yield self
        finally:
            result = self.pipeline.set_state(previous_state)
            if result == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError(f"Failed to set pipeline state to {state!r}")
        
    

class PushStateContextManager:
    def __init__(self, pipeline, new_state):
        self.pipeline = pipeline
        self.previous_state = None
        self.new_state = new_state

    def __enter__(self):
        _, current, _ = self.pipeline.get_state(0)
        self.previous_state = current

        result = self.pipeline.set_state(self.new_state)
        if result == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Failed to set pipeline state to {self.new_state!r}")

        return self.pipeline
    
    def __exit__(self, *_):
        if self.previous_state is not None:
            self.pipeline.set_state(self.previous_state)

        return False