def snake_to_camel(snake):
    return "".join(s.title() for s in snake.split("_"))
