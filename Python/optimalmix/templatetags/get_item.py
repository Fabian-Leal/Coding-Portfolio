from django.template.defaulttags import register


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def index(list, index):
    if index < len(list):
        return list[index]
    return None
