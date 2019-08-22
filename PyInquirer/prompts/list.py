# -*- coding: utf-8 -*-
"""
`list` type question
"""
from __future__ import print_function
from __future__ import unicode_literals

import math
import sys

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.filters import IsDone
from prompt_toolkit.layout.controls import TokenListControl
from prompt_toolkit.layout.containers import ConditionalContainer, \
    ScrollOffsets, HSplit
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.token import Token

from .. import PromptParameterException
from ..separator import Separator
from .common import if_mousedown, default_style

# custom control based on TokenListControl
# docu here:
# https://github.com/jonathanslenders/python-prompt-toolkit/issues/281
# https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/examples/full-screen-layout.py
# https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/docs/pages/full_screen_apps.rst


PY3 = sys.version_info[0] >= 3

if PY3:
    basestring = str


class InquirerControl(TokenListControl):
    def __init__(self, choices, page_size, **kwargs):
        self.selected_option_index = 0
        self.answered = False
        self.choices = choices
        self.current_page = 0
        page_size = page_size

        self.page_size = page_size if page_size > 0 else self.choice_count
        self.max_page = math.ceil(self.choice_count / page_size) if page_size > 0 else 0

        self._init_choices(choices)
        super(InquirerControl, self).__init__(self._get_choice_tokens,
                                              **kwargs)

    def _init_choices(self, choices, default=None):
        # helper to convert from question format to internal format
        self.choices = []  # list (name, value, disabled)
        searching_first_choice = True
        for i, c in enumerate(choices):
            if isinstance(c, Separator):
                self.choices.append((c, None, None))
            else:
                if isinstance(c, basestring):
                    self.choices.append((c, c, None))
                else:
                    name = c.get('name')
                    value = c.get('value', name)
                    disabled = c.get('disabled', None)
                    self.choices.append((name, value, disabled))
                if searching_first_choice:
                    self.selected_option_index = i  # found the first choice
                    searching_first_choice = False

    def increment_page(self):
        if self.max_page > 0:
            if self.current_page == self.max_page - 1:
                self.current_page = 0
            else:
                self.current_page += 1

            self.current_page = self.current_page % self.max_page
            self.selected_option_index = self.current_page * self.page_size

    def decrement_page(self):
        if self.max_page > 0:
            if self.current_page == 0:
                self.current_page = self.max_page - 1
            else:
                self.current_page -= 1

            self.current_page = self.current_page % self.max_page
            self.selected_option_index = self.current_page * self.page_size

    @property
    def choice_count(self):
        return len(self.choices)

    def _get_choice_tokens(self, cli):
        tokens = []
        T = Token

        def append(index, choice):
            selected = (index == self.selected_option_index)

            @if_mousedown
            def select_item(cli, mouse_event):
                # bind option with this index to mouse event
                self.selected_option_index = index
                self.answered = True
                cli.set_return_value(self.get_selection()[1])

            tokens.append((T.Pointer if selected else T, ' \u276f ' if selected
            else '   '))
            if selected:
                tokens.append((Token.SetCursorPosition, ''))
            if choice[2]:  # disabled
                tokens.append((T.Selected if selected else T,
                               '- %s (%s)' % (choice[0], choice[2])))
            else:
                try:
                    tokens.append((T.Selected if selected else T, str(choice[0]),
                                select_item))
                except:
                    tokens.append((T.Selected if selected else T, choice[0],
                                select_item))
            tokens.append((T, '\n'))
        # prepare the select choices
        starting_index = self.current_page * self.page_size
        ending_index = (self.current_page + 1) * self.page_size
        for i, choice in enumerate(self.choices):
            if starting_index <= i < ending_index:
                append(i, choice)

        tokens.pop()  # Remove last newline.

        if self.max_page > 0:
            tokens.append((T, '\n'))
            tokens.append((T, 'Page {} of {}\n'.format(self.current_page+1, self.max_page)))
        return tokens

    def get_selection(self):
        return self.choices[self.selected_option_index]

    def decrement_selected_index(self):
        def _prev():
            if self.max_page > 1 and self.selected_option_index == 0:
                self.decrement_page()
                self.selected_option_index = self.choice_count - 1
            elif self.max_page > 1 and (self.selected_option_index % self.page_size) == 0:
                self.decrement_page()
                self.selected_option_index = ((self.current_page + 1) * self.page_size - 1)
            else:
                self.selected_option_index = (
                        (self.selected_option_index - 1) % self.choice_count)
        _prev()
        while isinstance(self.choices[self.selected_option_index][0], Separator) or \
                self.choices[self.selected_option_index][2]:
            _prev()

    def increment_selected_index(self):
        def _next():
            if self.max_page > 1 and ((self.selected_option_index + 1) % self.page_size) == 0:
                self.increment_page()
            elif self.max_page > 1 and self.selected_option_index + 1 == self.choice_count:
                self.increment_page()
            else:
                self.selected_option_index = (
                    (self.selected_option_index + 1) % self.choice_count)
        _next()
        while isinstance(self.choices[self.selected_option_index][0], Separator) or \
                self.choices[self.selected_option_index][2]:
            _next()


def question(message, **kwargs):
    # TODO disabled, dict choices
    if not 'choices' in kwargs:
        raise PromptParameterException('choices')

    choices = kwargs.pop('choices', None)
    default = kwargs.pop('default', 0)  # TODO
    page_size = kwargs.pop('page_size', 0)
    qmark = kwargs.pop('qmark', '?')
    # TODO style defaults on detail level
    style = kwargs.pop('style', default_style)

    ic = InquirerControl(choices, page_size)

    def get_prompt_tokens(cli):
        tokens = []

        tokens.append((Token.QuestionMark, qmark))
        tokens.append((Token.Question, ' %s ' % message))
        if ic.answered:
            tokens.append((Token.Answer, ' ' + ic.get_selection()[0]))
        else:
            tokens.append((Token.Instruction, ' (Use arrow keys)'))
        return tokens

    # assemble layout
    layout = HSplit([
        Window(height=D.exact(1),
               content=TokenListControl(get_prompt_tokens)
        ),
        ConditionalContainer(
            Window(ic),
            filter=~IsDone()
        )
    ])

    # key bindings
    manager = KeyBindingManager.for_prompt()

    @manager.registry.add_binding(Keys.ControlQ, eager=True)
    @manager.registry.add_binding(Keys.ControlC, eager=True)
    def _(event):
        raise KeyboardInterrupt()
        # event.cli.set_return_value(None)

    @manager.registry.add_binding(Keys.Down, eager=True)
    def move_cursor_down(event):
        ic.increment_selected_index()

    @manager.registry.add_binding(Keys.Up, eager=True)
    def move_cursor_up(event):
        ic.decrement_selected_index()

    @manager.registry.add_binding(Keys.Left, eager=True)
    def move_page_left(event):
        ic.decrement_page()

    @manager.registry.add_binding(Keys.Right, eager=True)
    def move_page_right(event):
        ic.increment_page()

    @manager.registry.add_binding(Keys.Enter, eager=True)
    def set_answer(event):
        ic.answered = True
        event.cli.set_return_value(ic.get_selection()[1])

    return Application(
        layout=layout,
        key_bindings_registry=manager.registry,
        mouse_support=True,
        style=style
    )
