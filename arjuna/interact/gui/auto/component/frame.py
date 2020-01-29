import os

from arjuna import Arjuna
from arjuna.interact.gui.auto.element.guielement import GuiElement
from arjuna.interact.gui.auto.finder.emd import SimpleGuiElementMetaData
from arjuna.interact.gui.auto.source.parser import FrameSource
from arjuna.interact.gui.auto.base.configurable import Configurable

from arjuna.core.poller.conditions import *
from arjuna.core.poller.caller import *
from arjuna.core.exceptions import ChildWindowNotFoundError

class FrameConditions:

    def __init__(self, frame):
        self.__frame = frame

    @property
    def frame(self):
        return self.__frame

    def FrameIsPresent(self, lmd, *args, **kwargs):
        caller = DynamicCaller(self.frame._find_frame, lmd, *args, **kwargs)
        return CommandCondition(caller)

class FrameContainer(Configurable):

    def __init__(self, gui, iconfig=None):
        super().__init__(gui, iconfig)
        self.__gui = gui
        self.__automator = gui.automator
        self.__conditions = FrameConditions(self)

    @property
    def conditions(self):
        return self.__conditions

    @property
    def gui(self):
        return self.__gui

    @property
    def automator(self):
        return self.__automator

    @property
    def max_wait_time(self):
        return self.automator.config.guiauto_max_wait_time

    def __check_tag(self, wrapped_element):
        tag = wrapped_element.source.tag
        if tag.lower() != "iframe":
            raise Exception("The element should have a 'iframe' tag for IFrame element. Found: " + tag)

    def frame(self, locator_meta_data, iconfig=None):
        return self.conditions.FrameIsPresent(locator_meta_data, iconfig=iconfig).wait(max_wait_time=self.max_wait_time)

    def _find_frame(self, locator_meta_data, iconfig=None):
        iconfig = iconfig and iconfig or self.settings
        found = False
        frame = None
        for locator in locator_meta_data.locators: 
            try:
                if locator.ltype.name == "INDEX":
                    index = locator.lvalue
                    emd = SimpleGuiElementMetaData("xpath", "//iframe")
                    multi_element = self.automator.multi_element(self.gui, emd)
                    # multi_element.find()
                    try:
                        wrapped_element = multi_element[index]
                    except:
                        # In case another identifier is present it should be tried.
                        continue
                    self.__check_tag(wrapped_element)
                    frame = IPartialFrame(self.gui, self, multi_element, wrapped_element, iconfig=iconfig)
                else:
                    emd = SimpleGuiElementMetaData(locator.ltype.name, locator.lvalue)
                    wrapped_element = self.automator.element(self.gui, emd)
                    # wrapped_element.find()
                    self.__check_tag(wrapped_element)
                    frame = IFrame(self.gui, self, wrapped_element, iconfig=iconfig)

                return frame
            except WaitableError as f:
                continue  
            except Exception as e:
                raise Exception(str(e) + traceback.format_exc()) 

        print(locator_meta_data.locators)
        raise ChildFrameNotFoundError(*locator_meta_data.locators)

    def enumerate_frames(self):
        self.focus()
        emd = SimpleGuiElementMetaData("xpath", "//iframe")
        multi_element = self.automator.create_multielement(emd)
        ret_str = os.linesep.join(["--> " + s for s in multi_element.get_source()._get_root_content_as_list()])
        return self._source_parser.get_root_content() + os.linesep + ret_str

class DomRoot(FrameContainer):

    def __init__(self, gui):
        super().__init__(gui)
        self.__frame_context = "root"
        self._source_parser = self.automator.source

    @property
    def frame_context(self):
        return self.__frame_context

    def __set_frame_context_str(self, name):
        self.__frame_context = name
        Arjuna.get_logger().debug("Automator is in {} frame".format(self.__frame_context))
        print("Automator is in {} frame".format(self.__frame_context))

    def set_frame_context(self, frame):
        self.__set_frame_context_str(frame)

    def set_frame_context_as_root(self):
        self.__set_frame_context_str("root")  

    def is_in_root_context(self):
        return self.__frame_context == "root"

    def focus(self):
        self.automator.dispatcher.focus_on_dom_root()
        self.set_frame_context_as_root() 

    @property
    def get_source(self):
        self.focus()
        return self.automator.source

class IFrame(FrameContainer):

    def __init__(self, gui, dom_root, wrapped_element, iconfig=None):
        super().__init__(gui, iconfig=iconfig)
        self.__dom_root = dom_root
        self.__parent_frames = []
        self.__wrapped_element = wrapped_element
        self._source_parser = FrameSource(self)

    @property
    def dom_root(self):
        return self.__dom_root

    @property
    def wrapped_element(self):
        return self.__wrapped_element

    def set_parents(self, parents):
        self.__parent_frames = parents

    def _act(self, json_dict):
        return self.dom_root._act(json_dict)

    def _focus_on_parents(self):
        if self.__parent_frames:
            for parent in self.__parent_frames:
                parent.focus()

    def __reload_wrapped_element(self):
        self.wrapped_element.find()

    def focus(self):
        if not self.dom_root.is_in_root_context():
            self.dom_root.focus()
            self._focus_on_parents()
        # self.wrapped_element.find()
        self._source_parser.set_root_source(self.wrapped_element.source.content.root)
        self.automator.dispatcher.focus_on_frame(self.wrapped_element.dispatcher)
        self.dom_root.set_frame_context(self)

    def _get_html_content_from_remote(self):
        return self.automator.get_source()

    def get_wrapped_element(self):
        return self.wrapped_element

    @property
    def source(self):
        self._source_parser.load()
        return self._source_parser

    # def focus_on_parent(self):
    #     self._act(TestAutomatorActionBodyCreator.jump_to_parent_frame())
    #     if self.__parent_frames:
    #         self.dom_root.set_frame_context(self.__parent_frames[-1])
    #     else:
    #         self.dom_root.set_frame_context_as_root()

    @property
    def parent(self):
        if self.__parent_frames:
            return self.__parent_frames[-1]
        else:
            return self.dom_root


class IPartialFrame(IFrame):

    def __init__(self, gui, dom_root, melement, wrapped_element, iconfig=None):
        super().__init__(gui, dom_root, wrapped_element, iconfig=iconfig)
        self.__melement = melement

    def focus(self):
        # self.__melement.find()
        self.automator.dispatcher.focus_on_frame(self.wrapped_element.dispatcher)
        self.dom_root.set_frame_context(self)