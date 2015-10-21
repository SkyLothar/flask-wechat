import itertools
import os

from jinja2 import Environment, FileSystemLoader, StrictUndefined

__all__ = ["render_template", "snake_to_camel"]
__curdir__ = os.path.dirname(os.path.realpath(__file__))

env = Environment(
    loader=FileSystemLoader(os.path.join(__curdir__, "templates")),
    undefined=StrictUndefined
)


def render_template(template_name, **kwargs):
    template = env.get_template(template_name)
    return template.render(kwargs)


def snake_to_camel(snake):
    return "".join(s.title() for s in snake.split("_"))


def get_n(total, n):
    part = True
    while part:
        part = list(itertools.islice(total, n))
        if not part:
            return
        yield part
