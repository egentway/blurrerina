import gi
import logging
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

from collections.abc import Iterable
from itertools import tee


class PipelineWrapper:
    """
    Ergonomic wrapper to Gst.Pipeline.
    Takes care of some of the boilerplate and allows for easy access and linking
    of pipeline elements.
    """
    def __init__(self, pipeline: Gst.Pipeline, loop: GLib.MainLoop):
        self.loop = loop
        self.pipeline = pipeline
        if not self.pipeline:
            raise RuntimeError("Unable to create pipeline.")

        self.logger = logging.getLogger(repr(self))
        self._setup_bus()
    
    def __repr__(self):
        return f'{self.__class__.__name__}("{self.pipeline.name}")'
    
    def _setup_bus(self):
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message, self.loop)
    
    def _on_message(self, bus, message, loop):
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
        """
        Creates an element, adds it to the pipeline and sets its properties.
        """
        elem = Gst.ElementFactory.make(factory, name)
        if not elem:
            raise RuntimeError(f"Could not create element '{factory}'")
        
        if properties:
            for key, item in properties.items():
                elem.set_property(key, item)

        self.pipeline.add(elem)
        return elem
    
    def __getitem__(self, name: str):
        """
        Return pipeline's element called `name`. Throws `IndexError` if there's no such element.
        """
        element = self.pipeline.get_by_name(name)
        if element is None:
            raise IndexError(f"{self}: No element {name}")
        return element
    
    def link(self, names_or_elems: Iterable[str | Gst.Element]):
        """
        Links together elements. Elements can be specified with their name or their Gst.Element instance.
        """
        elems = (self[elem] if isinstance(elem, str) else elem for elem in names_or_elems)
        elems_a, elems_b = tee(elems)
        next(elems_b)
        for elem_a, elem_b in zip(elems_a, elems_b):
            success = elem_a.link(elem_b)
            if not success:
                raise RuntimeError(f"Failed to link {elem_a.name} → {elem_b.name}")
    
    def set_state(self, state: Gst.State):
        """
        Sets the pipeline state. Throws `RuntimeError` in case of failure.
        """
        self.logger.info(f"Setting {self} state to {state}")
        ret = self.pipeline.set_state(state)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Unable to set {self} to {state} state")
