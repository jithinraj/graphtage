"""A :class:`graphtage.Filetype` for parsing, diffing, and rendering `JSON files`_.

.. _JSON files:
    https://tools.ietf.org/html/std90

"""

import json
import os
from typing import Union

from .graphtage import BoolNode, DictNode, Filetype, FixedKeyDictNode, \
    FloatNode, IntegerNode, KeyValuePairNode, LeafNode, ListNode, StringFormatter, StringNode
from .printer import Fore, Printer
from .sequences import SequenceFormatter
from .tree import GraphtageFormatter, TreeNode


def build_tree(
        python_obj: Union[int, float, bool, str, bytes, list, dict],
        allow_key_edits: bool = True,
        force_leaf_node: bool = False) -> TreeNode:
    """Builds a Graphtage tree from an arbitrary Python object.

    Args:
        python_obj: The object from which to build the tree.
        allow_key_edits: Whether or not to try and match key/value pairs in dicts if their keys differ.
        force_leaf_node: If :const:`True`, assume that :obj:`python_obj` is *not* a :func:`list` or :func:`dict`.

    Returns:
        TreeNode: The resulting tree.

    Raises:
        ValueError: If :obj:`force_leaf_node` is :const:`True` and :obj:`python_obj` is *not* one of :class:`int`,
            :class:`float`, :class:`bool`, :class:`str`, or :class:`bytes`.
        ValueError: If the object is of an unsupported type.

    """
    if isinstance(python_obj, int):
        return IntegerNode(python_obj)
    elif isinstance(python_obj, float):
        return FloatNode(python_obj)
    elif isinstance(python_obj, bool):
        return BoolNode(python_obj)
    elif isinstance(python_obj, str):
        return StringNode(python_obj)
    elif isinstance(python_obj, bytes):
        return StringNode(python_obj.decode('utf-8'))
    elif force_leaf_node:
        raise ValueError(f"{python_obj!r} was expected to be an int or string, but was instead a {type(python_obj)}")
    elif isinstance(python_obj, list) or isinstance(python_obj, tuple):
        return ListNode([build_tree(n, allow_key_edits=allow_key_edits) for n in python_obj])
    elif isinstance(python_obj, dict):
        dict_items = {
            build_tree(k, allow_key_edits=allow_key_edits, force_leaf_node=True):
                build_tree(v, allow_key_edits=allow_key_edits) for k, v in python_obj.items()
        }
        if allow_key_edits:
            return DictNode.from_dict(dict_items)
        else:
            return FixedKeyDictNode.from_dict(dict_items)
    else:
        raise ValueError(f"Unsupported Python object {python_obj!r} of type {type(python_obj)}")


class JSONListFormatter(SequenceFormatter):
    """A sub-formatter for JSON lists."""
    is_partial = True

    def __init__(self):
        """Initializes the JSON list formatter.

        Equivalent to::

            super().__init__('[', ']', ',')

        """
        super().__init__('[', ']', ',')

    def print_ListNode(self, *args, **kwargs):
        """Prints a :class:`graphtage.ListNode`.

        Equivalent to::

            super().print_SequenceNode(*args, **kwargs)

        """
        super().print_SequenceNode(*args, **kwargs)

    def print_SequenceNode(self, *args, **kwargs):
        """Prints a non-List sequence.

        This delegates to the parent formatter's implementation::

            self.parent.print(*args, **kwargs)

        which should invoke :meth:`JSONFormatter.print`, thereby delegating to the :class:`JSONDictFormatter` in
        instances where a list contains a dict.

        """
        self.parent.print(*args, **kwargs)


class JSONDictFormatter(SequenceFormatter):
    """A sub-formatter for JSON dicts."""
    is_partial = True

    def __init__(self):
        super().__init__('{', '}', ',')

    def print_MultiSetNode(self, *args, **kwargs):
        """Prints a :class:`graphtage.MultiSetNode`.

        Equivalent to::

            super().print_SequenceNode(*args, **kwargs)

        """
        super().print_SequenceNode(*args, **kwargs)

    def print_MappingNode(self, *args, **kwargs):
        """Prints a :class:`graphtage.MappingNode`.

        Equivalent to::

            super().print_SequenceNode(*args, **kwargs)

        """
        super().print_SequenceNode(*args, **kwargs)

    def print_SequenceNode(self, *args, **kwargs):
        """Prints a non-Dict sequence.

        This delegates to the parent formatter's implementation::

            self.parent.print(*args, **kwargs)

        which should invoke :meth:`JSONFormatter.print`, thereby delegating to the :class:`JSONListFormatter` in
        instances where a dict contains a list.

        """
        self.parent.print(*args, **kwargs)


class JSONStringFormatter(StringFormatter):
    """A JSON formatter for strings."""
    is_partial = True

    def write_char(self, printer: Printer, c: str, index: int, num_edits: int, removed=False, inserted=False):
        """Writes a character, escaping if necessary.

        This is equivalent to::

            printer.write(json.dumps(c)[1:-1])

        """
        # json.dumps will enclose the string in quotes, so remove them
        printer.write(json.dumps(c)[1:-1])


class JSONFormatter(GraphtageFormatter):
    """The default JSON formatter."""
    sub_format_types = [JSONStringFormatter, JSONListFormatter, JSONDictFormatter]

    def print_LeafNode(self, printer: Printer, node: LeafNode):
        """Prints a :class:`graphtage.LeafNode`.

        This is equivalent to::

            printer.write(json.dumps(node.object))

        """
        printer.write(json.dumps(node.object))

    def print_KeyValuePairNode(self, printer: Printer, node: KeyValuePairNode):
        """Prints a :class:`graphtage.KeyValuePairNode`.

        By default, the key is printed in blue, followed by a bright ": ", followed by the value.

        """
        with printer.color(Fore.BLUE):
            self.print(printer, node.key)
        with printer.bright():
            printer.write(": ")
        self.print(printer, node.value)


class JSON(Filetype):
    """The JSON file type."""
    def __init__(self):
        """Initializes the JSON file type.

        By default, JSON associates itself with the "json", "application/json", "application/x-javascript",
        "text/javascript", "text/x-javascript", and "text/x-json" MIME types.

        """
        super().__init__(
            'json',
            'application/json',
            'application/x-javascript',
            'text/javascript',
            'text/x-javascript',
            'text/x-json'
        )

    def build_tree(self, path: str, allow_key_edits: bool = True) -> TreeNode:
        with open(path) as f:
            return build_tree(json.load(f), allow_key_edits=allow_key_edits)

    def build_tree_handling_errors(self, path: str, allow_key_edits: bool = True) -> Union[str, TreeNode]:
        try:
            return self.build_tree(path=path, allow_key_edits=allow_key_edits)
        except json.decoder.JSONDecodeError as de:
            return f'Error parsing {os.path.basename(path)}: {de.msg}: line {de.lineno}, column {de.colno} (char {de.pos})'

    def get_default_formatter(self) -> JSONFormatter:
        return JSONFormatter.DEFAULT_INSTANCE
