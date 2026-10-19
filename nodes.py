"""Assert nodes for ComfyUI.

Assert(number) - passes a number through, after checking it against a
                 Math Expression-style test that may also reference extra
                 inputs y, z, a, b, ... w.
Assert         - passes any value through, after checking a boolean input.

In both nodes the condition states how things SHOULD be: true lets the
workflow continue; false stops it with the configured error message.

Error messages may reference inputs with {x}, {y}, etc. Use {{ and }} for
literal braces.
"""

import math
import string

from simpleeval import simple_eval, NameNotDefined
from typing_extensions import override

from comfy_api.latest import ComfyExtension, io


MAX_EXPONENT = 4000

# x first, then y and z, then wrap around to a ... w (26 names in total).
VARIABLE_NAMES = ["x", "y", "z"] + list(string.ascii_lowercase[:23])
EXTRA_NAMES = VARIABLE_NAMES[1:]


class AssertionFailed(AssertionError):
    """Raised when an assert node's condition is false."""


def _variadic_sum(*args):
    """Support both sum(values) and sum(x, y, z)."""
    if len(args) == 1 and hasattr(args[0], "__iter__"):
        return sum(args[0])
    return sum(args)


def _safe_pow(base, exp):
    """pow() with an exponent cap, matching the core Math Expression node."""
    if abs(exp) > MAX_EXPONENT:
        raise ValueError(f"Exponent {exp} exceeds maximum allowed ({MAX_EXPONENT})")
    return pow(base, exp)


# Same function set as the core Math Expression node.
MATH_FUNCTIONS = {
    "sum": _variadic_sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "pow": _safe_pow,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "int": int,
    "float": float,
}


class _KeepUnknown(dict):
    """Leaves {placeholders} for unknown names in place instead of failing."""

    def __missing__(self, key):
        return "{" + key + "}"


def _format_message(message: str, values: dict) -> str:
    """Fill {x}-style placeholders; fall back to the raw text if it can't be formatted."""
    try:
        return message.format_map(_KeepUnknown(values))
    except (ValueError, IndexError, KeyError, AttributeError, TypeError):
        return message


def _fail(message: str, values: dict):
    text = _format_message(message, values).strip() or "Assertion failed."
    raise AssertionFailed(text)


class AssertNumber(io.ComfyNode):
    """Pass a number through only if a Math Expression-style test is true."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        extras = io.Autogrow.TemplateNames(
            input=io.MultiType.Input("value", [io.Int, io.Float, io.Boolean]),
            names=EXTRA_NAMES,
            min=1,
        )
        return io.Schema(
            node_id="ComfyUIAssert_AssertNumber",
            display_name="Assert(number)",
            category="utilities/assert",
            search_aliases=["assert", "check", "validate", "guard", "require"],
            description=(
                "Passes x through if the test is true; otherwise stops the "
                "workflow with the error message."
            ),
            inputs=[
                io.MultiType.Input("x", [io.Int, io.Float], display_name="x"),
                io.Autogrow.Input("values", template=extras),
                io.String.Input(
                    "test",
                    default="x % y == 0",
                    multiline=True,
                    tooltip=(
                        "Math Expression-style test describing what should be true. "
                        "Refer to inputs by name: x, y, z, a, b, ..."
                    ),
                ),
                io.String.Input(
                    "error_message",
                    default="x ({x}) is not divisible by y ({y}).",
                    multiline=True,
                    tooltip=(
                        "Shown when the test is false. {x}, {y}, etc. are replaced "
                        "with the input values; use {{ and }} for literal braces."
                    ),
                ),
            ],
            outputs=[
                io.Int.Output(display_name="x as int"),
                io.Float.Output(display_name="x as float"),
            ],
        )

    @classmethod
    def execute(cls, x, values: io.Autogrow.Type, test: str, error_message: str) -> io.NodeOutput:
        if not test.strip():
            raise ValueError("Assert(number): the test expression is empty.")

        context = {"x": x}
        context.update({k: v for k, v in dict(values).items() if v is not None})
        context["values"] = list(context.values())

        try:
            result = simple_eval(test, names=context, functions=MATH_FUNCTIONS)
        except NameNotDefined as e:
            name = getattr(e, "name", None)
            if name in VARIABLE_NAMES:
                raise ValueError(
                    f"Assert(number): the test '{test.strip()}' uses '{name}', "
                    f"but nothing is connected to the '{name}' input."
                ) from None
            raise ValueError(f"Assert(number): unknown name in test '{test.strip()}': {e}") from None
        except Exception as e:
            raise ValueError(
                f"Assert(number): couldn't evaluate test '{test.strip()}': {e}"
            ) from None

        if not isinstance(result, (bool, int, float)):
            raise ValueError(
                f"Assert(number): the test '{test.strip()}' must evaluate to true/false "
                f"or a number, got {type(result).__name__}: {result!r}"
            )

        if not result:
            _fail(error_message, context)

        if isinstance(x, float):
            if not math.isfinite(x):
                raise ValueError(f"Assert(number): x is {x}, which can't be converted to an int.")
            return io.NodeOutput(int(x), x)
        return io.NodeOutput(int(x), float(x))


class Assert(io.ComfyNode):
    """Pass any value through only if a boolean condition is true."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        x_type = io.MatchType.Template("x_type")
        return io.Schema(
            node_id="ComfyUIAssert_Assert",
            display_name="Assert",
            category="utilities/assert",
            search_aliases=["assert", "check", "validate", "guard", "require"],
            description=(
                "Passes x through if condition is true; otherwise stops the "
                "workflow with the error message."
            ),
            inputs=[
                io.MatchType.Input("x", template=x_type, display_name="x"),
                io.Boolean.Input(
                    "condition",
                    force_input=True,
                    tooltip="What should be true. If false, the workflow stops with the error message.",
                ),
                io.String.Input(
                    "error_message",
                    default="Assertion failed.",
                    multiline=True,
                    tooltip=(
                        "Shown when the condition is false. {x} is replaced with "
                        "the input value; use {{ and }} for literal braces."
                    ),
                ),
            ],
            outputs=[
                io.MatchType.Output(template=x_type, display_name="x"),
            ],
        )

    @classmethod
    def execute(cls, x, condition: bool, error_message: str) -> io.NodeOutput:
        if not condition:
            _fail(error_message, {"x": x})
        return io.NodeOutput(x)


class AssertExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [AssertNumber, Assert]


async def comfy_entrypoint() -> AssertExtension:
    return AssertExtension()
