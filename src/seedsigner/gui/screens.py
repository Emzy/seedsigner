
from .components import (EDGE_PADDING, COMPONENT_PADDING, TOP_NAV_TITLE_FONT_SIZE,
    BUTTON_FONT_NAME, BUTTON_FONT_SIZE, Button, IconButton, TopNav, TextArea)

from dataclasses import dataclass
from PIL import ImageFont
from seedsigner.helpers import B, Buttons


RET_CODE__BACK_BUTTON = -1
RET_CODE__POWER_BUTTON = -2



@dataclass
class BaseScreen:
    # Avoid setting defaults on parent dataclasses, otherwise you must have defaults on
    #   all child attrs. see: https://stackoverflow.com/a/53085935
    # No base attrs specified yet


    def __post_init__(self):
        from seedsigner.gui import Renderer
        self.renderer = Renderer.get_instance()
        self.hw_inputs = Buttons.get_instance()

        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height


    def display(self):
        self._render()
        self.renderer.show_image()

        return self._run()


    def _render(self):
        # Clear the whole canvas
        self.renderer.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), fill=0)


    def _run(self):
        """
            Screen can run on its own until it returns a final exit input from the user.

            For example: A basic menu screen where the user can key up and down. The
            Screen can handle the UI updates to light up the currently selected menu item
            on its own. Only when the user clicks to make a selection would run() exit
            and returns the selected option.

            But an alternate use case returns immediately after each user input so the
            View can update its controlling logic accordingly (e.g. as the user joysticks
            over different letters in the keyboard UI, we need to make matching changes
            to the list of mnemonic seed words that match the new letter).

            In this case, it would be called repeatedly in a loop:
            * run() and wait for it to handle user input
            * run() exits and returns the user input (e.g. KEY_UP)
            * View updates its state of the world accordingly
            * loop and call run() again
        """
        raise Exception("Must implement in a child class")



@dataclass
class BaseTopNavScreen(BaseScreen):
    title: str
    title_font_size: int = TOP_NAV_TITLE_FONT_SIZE
    show_back_button: bool = True
    show_power_button: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.top_nav = TopNav(
            text=self.title,
            font_size=self.title_font_size,
            width=self.canvas_width,
            height=48,
            show_back_button=self.show_back_button,
            show_power_button=self.show_power_button,
        )
        self.is_input_in_top_nav = False


    def _render(self):
        super()._render()
        self.top_nav.render()


    def _run(self):
        raise Exception("Must implement in a child class")


@dataclass
class TextTopNavScreen(BaseTopNavScreen):
    text: str = "Your display text"
    is_text_centered: bool = True
    text_font_name: str = "OpenSans-Regular"
    text_font_size: int = 17
    supersampling_factor: int = None

    def __post_init__(self):
        super().__post_init__()
        if self.text_font_size < 18 and not self.supersampling_factor or self.supersampling_factor == 1:
            self.supersampling_factor = 2

        self.text_area = TextArea(
            text=self.text,
            screen_x=0,
            screen_y=self.top_nav.height,
            width=self.canvas_width,
            height=self.canvas_height - self.top_nav.height,
            font_name=self.text_font_name,
            font_size=self.text_font_size,
            is_text_centered=self.is_text_centered,
            supersampling_factor=self.supersampling_factor
        )


    def _render(self):
        super()._render()
        self.top_nav.render()
        self.text_area.render()


    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if user_input == B.KEY_UP:
                if not self.top_nav.is_selected:
                    self.top_nav.is_selected = True
                    self.top_nav.render()

            elif user_input == B.KEY_DOWN:
                if self.top_nav.is_selected:
                    self.top_nav.is_selected = False
                    self.top_nav.render()

            elif user_input == B.KEY_PRESS:
                if self.top_nav.is_selected:
                    return self.top_nav.selected_button

            # Write the screen updates
            self.renderer.show_image()


@dataclass
class ButtonListScreen(BaseTopNavScreen):
    button_labels: list = None                  # w/Python 3.9 we can be more specific: list[str]
    selected_button: int = 0
    is_button_text_centered: bool = True
    is_bottom_list: bool = False
    button_font_name: str = BUTTON_FONT_NAME
    button_font_size: int = BUTTON_FONT_SIZE
    button_selected_color: str = "orange"

    def __post_init__(self):
        super().__post_init__()

        button_height = int(self.canvas_height * 3.0 / 20.0)    # 36px on a 240x240 screen
        if len(self.button_labels) == 1:
            button_list_height = button_height
        else:
            button_list_height = (len(self.button_labels) * button_height) + (COMPONENT_PADDING * (len(self.button_labels) - 1))

        if self.is_bottom_list:
            button_list_y = self.canvas_height - (button_list_height + EDGE_PADDING)
        else:
            button_list_y = self.top_nav.height + int((self.canvas_height - self.top_nav.height - button_list_height) / 2)

        if button_list_y < self.top_nav.height:
            # The button list is too long; force it to run off the bottom of the screen.
            button_list_y = self.top_nav.height

        self.buttons = []
        for i, button_label in enumerate(self.button_labels):
            button = Button(
                text=button_label,
                screen_x=EDGE_PADDING,
                screen_y=button_list_y + i * (button_height + COMPONENT_PADDING),
                width=self.canvas_width - (2 * EDGE_PADDING),
                height=button_height,
                is_text_centered=self.is_button_text_centered,
                font_name=self.button_font_name,
                font_size=self.button_font_size,
                selected_color=self.button_selected_color
            )
            self.buttons.append(button)

        self.buttons[0].is_selected = True
        self.selected_button = 0


    def _render(self):
        super()._render()
        for button in self.buttons:
            button.render()


    def _run(self):
        while True:
            user_input = self.hw_inputs.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if user_input == B.KEY_UP:
                if self.selected_button == 0:
                    # Move selection up to top_nav
                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()
                    self.selected_button = None

                    self.top_nav.is_selected = True
                    self.top_nav.render()
                else:
                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()
                    self.selected_button -= 1
                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

            elif user_input == B.KEY_DOWN:
                if self.top_nav.is_selected:
                    self.top_nav.is_selected = False
                    self.top_nav.render()

                    self.selected_button = 0
                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

                elif self.selected_button == len(self.buttons) - 1:
                    # TODO: Trap selection at bottom or loop?
                    pass
                else:
                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()
                    self.selected_button += 1
                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()

            elif user_input == B.KEY_PRESS:
                if self.top_nav.is_selected:
                    return self.top_nav.selected_button
                return self.selected_button

            # Write the screen updates
            self.renderer.show_image()



class BottomButtonScreen(ButtonListScreen):
    def __init__(self,
                 title: str,
                 button_data: list,
                 is_button_text_centered: bool,
                 title_font: ImageFont = None,
                 body_text: str = None,
                 is_body_text_centered: bool = True,
                 body_font_color: str = None,
                 body_font_name: str = None,
                 body_font_size: int = None,
                 button_font: ImageFont = None,
                 supersampling_factor: int = None):
        super().__init__(
            title=title,
            button_data=button_data,
            is_button_text_centered=is_button_text_centered,
            is_bottom_list=True,
            title_font=title_font,
            button_font=button_font
        )

        self.body_textscreen = TextArea(
            text=body_text,
            screen_x=0,
            screen_y=self.top_nav.height,
            width=self.canvas_width,
            height=self.buttons[0].screen_y - self.top_nav.height,
            font_name=body_font_name,
            font_size=body_font_size,
            font_color=body_font_color,
            is_text_centered=is_body_text_centered,
            supersampling_factor=supersampling_factor
        )


    def _render(self):
        self.renderer.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), fill=0)
        self.top_nav.render()
        self.body_textscreen.render()
        for button in self.buttons:
            button.render()
        self.renderer.show_image()



@dataclass
class LargeButtonScreen(BaseTopNavScreen):
    button_data: list = None           # list of tuples: (display_text: str, display_icon: str = None)
    button_font_name: str = BUTTON_FONT_NAME
    button_font_size: int = 20
    button_selected_color: str = "orange"

    def __post_init__(self):
        super().__post_init__()

        if len(self.button_data) not in [2, 4]:
            raise Exception("LargeButtonScreen only supports 2 or 4 buttons")

        # Maximize 2-across width; calc height with a 4:3 aspect ratio
        button_width = int((self.canvas_width - (2 * EDGE_PADDING) - COMPONENT_PADDING) / 2)
        button_height = int(button_width * (3.0 / 4.0))

        # Vertically center the buttons
        if len(self.button_data) == 2:
            button_start_y = self.top_nav.height + int((self.canvas_height - (self.top_nav.height + COMPONENT_PADDING) - button_height) / 2)
        else:
            button_start_y = self.top_nav.height + int((self.canvas_height - (self.top_nav.height + COMPONENT_PADDING) - (2 * button_height) - COMPONENT_PADDING) / 2)

        self.buttons = []
        for i, (button_label, button_icon_name) in enumerate(self.button_data):
            if i % 2 == 0:
                button_start_x = EDGE_PADDING
            else:
                button_start_x = EDGE_PADDING + button_width + COMPONENT_PADDING

            button_args = {
                "text": button_label,
                "screen_x": button_start_x,
                "screen_y": button_start_y,
                "width": button_width,
                "height": button_height,
                "is_text_centered": True,
                "font_name": self.button_font_name,
                "font_size": self.button_font_size,
                "selected_color": self.button_selected_color,
            }
            if button_icon_name:
                button_args["icon_name"] = button_icon_name
                button_args["text_y_offset"] = int(48 / 240 * self.renderer.canvas_height)
                button = IconButton(**button_args)
            else:
                button = Button(**button_args)

            self.buttons.append(button)

            if i == 1:
                button_start_y += button_height + COMPONENT_PADDING

        self.buttons[0].is_selected = True
        self.selected_button = 0


    def _render(self):
        super()._render()
        for button in self.buttons:
            button.render()


    def _run(self):
        def swap_selected_button(new_selected_button: int):
            self.buttons[self.selected_button].is_selected = False
            self.buttons[self.selected_button].render()
            self.selected_button = new_selected_button
            self.buttons[self.selected_button].is_selected = True
            self.buttons[self.selected_button].render()

        while True:
            user_input = self.hw_inputs.wait_for([B.KEY_UP, B.KEY_DOWN, B.KEY_LEFT, B.KEY_RIGHT, B.KEY_PRESS], check_release=True, release_keys=[B.KEY_PRESS])
            if user_input == B.KEY_UP:
                if self.selected_button in [0, 1]:
                    # Move selection up to top_nav
                    self.top_nav.is_selected = True
                    self.top_nav.render()

                    self.buttons[self.selected_button].is_selected = False
                    self.buttons[self.selected_button].render()

                elif len(self.buttons) == 4:
                    swap_selected_button(self.selected_button - 2)

            elif user_input == B.KEY_DOWN:
                if self.top_nav.is_selected:
                    self.top_nav.is_selected = False
                    self.top_nav.render()

                    self.buttons[self.selected_button].is_selected = True
                    self.buttons[self.selected_button].render()
                elif self.selected_button in [2, 3]:
                    # TODO: Trap selection at bottom or loop?
                    pass
                elif len(self.buttons) == 4:
                    swap_selected_button(self.selected_button + 2)

            elif user_input == B.KEY_RIGHT and not self.top_nav.is_selected:
                if self.selected_button in [0, 2]:
                    swap_selected_button(self.selected_button + 1)

            elif user_input == B.KEY_LEFT and not self.top_nav.is_selected:
                if self.selected_button in [1, 3]:
                    swap_selected_button(self.selected_button - 1)

            elif user_input == B.KEY_PRESS:
                if self.top_nav.is_selected:
                    return self.top_nav.selected_button
                return self.selected_button

            # Write the screen updates
            self.renderer.show_image()



class FontTesterScreen(ButtonListScreen):
    def __init__(self,
                 title: str,
                 button_data: list,
                 is_text_centered: bool,
                 is_bottom_list: bool,
                 font: ImageFont,
                 button_font: ImageFont):
        super().__init__(
            title=title,
            button_data=button_data,
            is_text_centered=is_text_centered,
            is_bottom_list=is_bottom_list,
            font=font,
            button_font=button_font
        )
