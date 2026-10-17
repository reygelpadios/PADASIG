from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def label(context, filipino, english):
    return english if context.get("lang") == "en" else filipino
