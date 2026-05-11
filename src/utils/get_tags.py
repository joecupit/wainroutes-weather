from bs4 import ResultSet, Tag


def get_tag_by_class(tag: Tag | None, class_name: str) -> Tag | None:
    """Given a bs4 Tag, return the first Tag within matching class_name (or None)"""
    if tag is None:
        return None

    inner_tag = tag.find(class_=class_name)
    if not isinstance(inner_tag, Tag):
        return None

    return inner_tag


def get_all_tags_by_class(tag: Tag | None, class_name: str) -> ResultSet:
    """Given a bs4 Tag, return all Tags within matching class_name (or None)"""
    if tag is None:
        return ResultSet([])

    inner_tags = tag.find_all(class_=class_name)
    return inner_tags


def get_tag_in_tag(tag: Tag | None, tag_name: str) -> Tag | None:
    """Given a bs4 Tag, return the first tag_name Tag within (or None)"""
    if tag is None:
        return None

    inner_tag = tag.find(tag_name)
    if not isinstance(inner_tag, Tag):
        return None

    return inner_tag


def get_all_tags_in_tag(tag: Tag | None, tag_name: str) -> ResultSet:
    """Given a bs4 Tag, return all tag_name Tags within (or None)"""
    if tag is None:
        return ResultSet([])

    inner_tags = tag.find_all(tag_name)
    return inner_tags


def get_text_from_tag(tag: Tag | None) -> str:
    """Given a bs4 Tag, return all raw text within"""
    if tag is None:
        return ""

    return " ".join(tag.text.strip().split())


def get_text_from_p_in_class(tag: Tag | None, class_name: str):
    """Given a bs4 Tag, return all raw text within its first p Tag"""
    return get_text_from_tag(get_tag_in_tag(get_tag_by_class(tag, class_name), "p"))
