from __future__ import division, print_function

from functools import partial, wraps

import inspect
import sys

from pyparsing import (
    delimitedList,
    Literal,
    Optional,
    Forward,
    Word,
    Group,
    QuotedString,
    nums,
    alphas,
    alphanums,
)


def composition(f, *gs):
    return lambda x: f(
        (
            composition(*gs) if gs else lambda x: x
        )(
            x
        )
    )


def parse_action(f):
    """
    Decorator for pyparsing parse actions to ease debugging.

    pyparsing uses trial & error to deduce the number of arguments a parse
    action accepts. Unfortunately any ``TypeError`` raised by a parse action
    confuses that mechanism.

    This decorator replaces the trial & error mechanism with one based on
    reflection. If the decorated function itself raises a ``TypeError`` then
    that exception is re-raised if the wrapper is called with less arguments
    than required. This makes sure that the actual ``TypeError`` bubbles up
    from the call to the parse action (instead of the one caused by pyparsing's
    trial & error).
    """
    num_args = len(inspect.getargspec(f).args)
    if num_args > 3:
        raise ValueError('Input function must take at most 3 parameters.')

    @wraps(f)
    def action(*args):
        if len(args) < num_args:
            if action.exc_info:
                raise action.exc_info[0], action.exc_info[1], action.exc_info[2]
        action.exc_info = None
        try:
            return f(*args[:-(num_args + 1):-1])
        except TypeError:
            action.exc_info = sys.exc_info()
            raise

    action.exc_info = None

    return action


def syntax():
    """https://docs.python.org/2/reference/expressions.html
    """

    identifier = Word(alphas+'_', alphanums+'_')
    string_ = (
        QuotedString('"') | QuotedString("'")
    ).setParseAction(composition(str, ''.join))
    # FIXME unicode string (how is this handled in python 3?) important to be
    # able to destinguice between unicode and not
    unicode_string = (
        Literal('u').suppress() + string_
    ).setParseAction(composition(unicode, u''.join))
    integer = (
        Optional(Literal('-'), default='+') + Word(nums)
    ).setParseAction(composition(int, ''.join))
    long_ = (
        integer + Literal('L').suppress()
    ).setParseAction(composition(long, ''.join, partial(map, str)))
    float_ = (
        Optional(integer, default=0) + Literal('.') + Optional(Word(nums), default='0')
    ).setParseAction(composition(float, ''.join, partial(map, str)))
    # TODO complex
    number = float_ | long_ | integer
    atom = unicode_string | string_ | number

    expression = Forward()  # FIXME name of this?
    dictionary = Group(
        Literal('{').suppress() + delimitedList(
            expression + Literal(':').suppress() + expression
        )
    ).setParseAction(list)
    set_ = Group(
        Literal('{').suppress() + delimitedList(
            expression
        ) + Literal('}').suppress()
    ).setParseAction(list)
    list_ = Group(
        Literal('[').suppress() + delimitedList(
            expression
        ) + Literal(']').suppress()
    ).setParseAction(list)
    tuple_ = Group(
        Literal('(').suppress() + delimitedList(
            expression
        ) + Literal(')').suppress()
    ).setParseAction(tuple)

    instance = identifier + tuple_

    expression << (atom | tuple_ | instance | dictionary | set_ | list_)

    return expression

#print(syntax().parseString('{[u"234", \'123\', [1L,(2.0, .2, 1.),-2, "3"]]}', parseAll=True).asList()[0])
print(syntax().parseString('[{1:1}, {3:2}]').asList()[0])
