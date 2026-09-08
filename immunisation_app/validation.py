"""Validate all accepted GET fields, including repeated and unexpected keys."""
import math

class InvalidFilters(ValueError):
    pass

class Filters:
    def __init__(self, args, allowed):
        self.args = args
        if any(key not in allowed for key in args):
            raise InvalidFilters("An unrecognised filter was supplied. Reset the form and try again.")
        if any(len(args.getlist(key)) != 1 for key in args):
            raise InvalidFilters("Each filter must be supplied once.")
        if any(len(value)>200 for value in args.values()):
            raise InvalidFilters("A filter value is too long.")

    def choice(self, key, allowed, default):
        value = self.args.get(key, str(default))
        if value not in {str(item) for item in allowed}:
            raise InvalidFilters(f"Choose a valid {key.replace('_',' ')}.")
        return value

    def integer(self, key, default, low, high):
        text = self.args.get(key, str(default))
        if not text.isascii() or not text.isdigit() or len(text)>9:
            raise InvalidFilters(f"{key.capitalize()} must be a whole number.")
        value = int(text)
        if not low <= value <= high:
            raise InvalidFilters(f"{key.capitalize()} must be between {low} and {high}.")
        return value

    def number(self, key, default=None, low=0, high=1e15):
        text = self.args.get(key, default)
        if text is None or text == "":
            return default
        try:
            value = float(text)
        except (ValueError,TypeError):
            raise InvalidFilters(f"{key.replace('_',' ').capitalize()} must be a number.") from None
        if not math.isfinite(value) or not low<=value<=high:
            raise InvalidFilters(f"{key.replace('_',' ').capitalize()} must be between {low:g} and {high:g}.")
        return value

    def text(self, key, default="", max_length=80):
        value = self.args.get(key, default).strip()
        if len(value)>max_length or any(ord(ch)<32 for ch in value):
            raise InvalidFilters(f"{key.capitalize()} must be at most {max_length} characters with no control characters.")
        return value

    def range(self, column):
        lower = self.number("min_"+column)
        upper = self.number("max_"+column)
        if lower is not None and upper is not None and lower>upper:
            raise InvalidFilters(f"Minimum {column} cannot exceed maximum {column}.")
        return {"min_"+column:lower,"max_"+column:upper}

