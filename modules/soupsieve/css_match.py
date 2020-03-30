"""CSS matcher."""
from datetime import datetime
from . import util
import re
from .import css_types as ct
import unicodedata

# Empty tag pattern (whitespace okay)
RE_NOT_EMPTY = re.compile('[^ \t\r\n\f]')

RE_NOT_WS = re.compile('[^ \t\r\n\f]+')

# Relationships
REL_PARENT = ' '
REL_CLOSE_PARENT = '>'
REL_SIBLING = '~'
REL_CLOSE_SIBLING = '+'

# Relationships for :has() (forward looking)
REL_HAS_PARENT = ': '
REL_HAS_CLOSE_PARENT = ':>'
REL_HAS_SIBLING = ':~'
REL_HAS_CLOSE_SIBLING = ':+'

NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_XML = 'http://www.w3.org/XML/1998/namespace'

DIR_FLAGS = ct.SEL_DIR_LTR | ct.SEL_DIR_RTL
RANGES = ct.SEL_IN_RANGE | ct.SEL_OUT_OF_RANGE

DIR_MAP = {
    'ltr': ct.SEL_DIR_LTR,
    'rtl': ct.SEL_DIR_RTL,
    'auto': 0
}

RE_NUM = re.compile(r"^(?P<value>-?(?:[0-9]{1,}(\.[0-9]+)?|\.[0-9]+))$")
RE_TIME = re.compile(r'^(?P<hour>[0-9]{2}):(?P<minutes>[0-9]{2})$')
RE_MONTH = re.compile(r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})$')
RE_WEEK = re.compile(r'^(?P<year>[0-9]{4,})-W(?P<week>[0-9]{2})$')
RE_DATE = re.compile(r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})$')
RE_DATETIME = re.compile(
    r'^(?P<year>[0-9]{4,})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})T(?P<hour>[0-9]{2}):(?P<minutes>[0-9]{2})$'
)
RE_WILD_STRIP = re.compile(r'(?:(?:-\*-)(?:\*(?:-|$))*|-\*$)')

MONTHS_30 = (4, 6, 9, 11)  # April, June, September, and November
FEB = 2
SHORT_MONTH = 30
LONG_MONTH = 31
FEB_MONTH = 28
FEB_LEAP_MONTH = 29
DAYS_IN_WEEK = 7


class _FakeParent(object):
    """
    Fake parent class.

    When we have a fragment with no `BeautifulSoup` document object,
    we can't evaluate `nth` selectors properly.  Create a temporary
    fake parent so we can traverse the root element as a child.
    """

    def __init__(self, element):
        """Initialize."""

        self.contents = [element]

    def __len__(self):
        """Length."""

        return len(self.contents)


class _DocumentNav(object):
    """Navigate a Beautiful Soup document."""

    @classmethod
    def assert_valid_input(cls, tag):
        """Check if valid input tag or document."""

        # Fail on unexpected types.
        if not cls.is_tag(tag):
            raise TypeError("Expected a BeautifulSoup 'Tag', but instead recieved type {}".format(type(tag)))

    @staticmethod
    def is_doc(obj):
        """Is `BeautifulSoup` object."""

        from modules import bs4
        return isinstance(obj, bs4.BeautifulSoup)

    @staticmethod
    def is_tag(obj):
        """Is tag."""

        from modules import bs4
        return isinstance(obj, bs4.Tag)

    @staticmethod
    def is_declaration(obj):  # pragma: no cover
        """Is declaration."""

        from modules import bs4
        return isinstance(obj, bs4.Declaration)

    @staticmethod
    def is_cdata(obj):
        """Is CDATA."""

        from modules import bs4
        return isinstance(obj, bs4.CData)

    @staticmethod
    def is_processing_instruction(obj):  # pragma: no cover
        """Is processing instruction."""

        from modules import bs4
        return isinstance(obj, bs4.ProcessingInstruction)

    @staticmethod
    def is_navigable_string(obj):
        """Is navigable string."""

        from modules import bs4
        return isinstance(obj, bs4.NavigableString)

    @staticmethod
    def is_special_string(obj):
        """Is special string."""

        from modules import bs4
        return isinstance(obj, (bs4.Comment, bs4.Declaration, bs4.CData, bs4.ProcessingInstruction, bs4.Doctype))

    @classmethod
    def is_content_string(cls, obj):
        """Check if node is content string."""

        return cls.is_navigable_string(obj) and not cls.is_special_string(obj)

    @staticmethod
    def create_fake_parent(el):
        """Create fake parent for a given element."""

        return _FakeParent(el)

    @staticmethod
    def is_xml_tree(el):
        """Check if element (or document) is from a XML tree."""

        return el._is_xml

    def is_iframe(self, el):
        """Check if element is an `iframe`."""

        return ((el.name if self.is_xml_tree(el) else util.lower(el.name)) == 'iframe') and self.is_html_tag(el)

    def is_root(self, el):
        """
        Return whether element is a root element.

        We check that the element is the root of the tree (which we have already pre-calculated),
        and we check if it is the root element under an `iframe`.
        """

        root = self.root and self.root is el
        if not root:
            parent = self.get_parent(el)
            root = parent is not None and self.is_html and self.is_iframe(parent)
        return root

    def get_contents(self, el, no_iframe=False):
        """Get contents or contents in reverse."""
        if not no_iframe or not self.is_iframe(el):
            for content in el.contents:
                yield content

    def get_children(self, el, start=None, reverse=False, tags=True, no_iframe=False):
        """Get children."""

        if not no_iframe or not self.is_iframe(el):
            last = len(el.contents) - 1
            if start is None:
                index = last if reverse else 0
            else:
                index = start
            end = -1 if reverse else last + 1
            incr = -1 if reverse else 1

            if 0 <= index <= last:
                while index != end:
                    node = el.contents[index]
                    index += incr
                    if not tags or self.is_tag(node):
                        yield node

    def get_descendants(self, el, tags=True, no_iframe=False):
        """Get descendants."""

        if not no_iframe or not self.is_iframe(el):
            next_good = None
            for child in el.descendants:

                if next_good is not None:
                    if child is not next_good:
                        continue
                    next_good = None

                is_tag = self.is_tag(child)

                if no_iframe and is_tag and self.is_iframe(child):
                    if child.next_sibling is not None:
                        next_good = child.next_sibling
                    else:
                        last_child = child
                        while self.is_tag(last_child) and last_child.contents:
                            last_child = last_child.contents[-1]
                        next_good = last_child.next_element
                    yield child
                    if next_good is None:
                        break
                    # Coverage isn't seeing this even though it's executed
                    continue  # pragma: no cover

                if not tags or is_tag:
                    yield child

    def get_parent(self, el, no_iframe=False):
        """Get parent."""

        parent = el.parent
        if no_iframe and parent is not None and self.is_iframe(parent):
            parent = None
        return parent

    @staticmethod
    def get_tag_name(el):
        """Get tag."""

        return el.name

    @staticmethod
    def get_prefix_name(el):
        """Get prefix."""

        return el.prefix

    @staticmethod
    def get_uri(el):
        """Get namespace `URI`."""

        return el.namespace

    @classmethod
    def get_next(cls, el, tags=True):
        """Get next sibling tag."""

        sibling = el.next_sibling
        while tags and not cls.is_tag(sibling) and sibling is not None:
            sibling = sibling.next_sibling
        return sibling

    @classmethod
    def get_previous(cls, el, tags=True):
        """Get previous sibling tag."""

        sibling = el.previous_sibling
        while tags and not cls.is_tag(sibling) and sibling is not None:
            sibling = sibling.previous_sibling
        return sibling

    @staticmethod
    def has_html_ns(el):
        """
        Check if element has an HTML namespace.

        This is a bit different than whether a element is treated as having an HTML namespace,
        like we do in the case of `is_html_tag`.
        """

        ns = getattr(el, 'namespace') if el else None
        return ns and ns == NS_XHTML

    @staticmethod
    def split_namespace(el, attr_name):
        """Return namespace and attribute name without the prefix."""

        return getattr(attr_name, 'namespace', None), getattr(attr_name, 'name', None)

    @staticmethod
    def get_attribute_by_name(el, name, default=None):
        """Get attribute by name."""

        value = default
        if el._is_xml:
            try:
                value = el.attrs[name]
            except KeyError:
                pass
        else:
            for k, v in el.attrs.items():
                if util.lower(k) == name:
                    value = v
                    break
        return value

    @staticmethod
    def iter_attributes(el):
        """Iterate attributes."""

        for k, v in el.attrs.items():
            yield k, v

    @classmethod
    def get_classes(cls, el):
        """Get classes."""

        classes = cls.get_attribute_by_name(el, 'class', [])
        if isinstance(classes, str):
            classes = RE_NOT_WS.findall(classes)
        return classes

    def get_text(self, el, no_iframe=False):
        """Get text."""

        return ''.join(
            [node for node in self.get_descendants(el, tags=False, no_iframe=no_iframe) if self.is_content_string(node)]
        )


class Inputs(object):
    """Class for parsing and validating input items."""

    @staticmethod
    def validate_day(year, month, day):
        """Validate day."""

        max_days = LONG_MONTH
        if month == FEB:
            max_days = FEB_LEAP_MONTH if ((year % 4 == 0) and (year % 100 != 0)) or (year % 400 == 0) else FEB_MONTH
        elif month in MONTHS_30:
            max_days = SHORT_MONTH
        return 1 <= day <= max_days

    @staticmethod
    def validate_week(year, week):
        """Validate week."""

        max_week = datetime.strptime("{}-{}-{}".format(12, 31, year), "%m-%d-%Y").isocalendar()[1]
        if max_week == 1:
            max_week = 53
        return 1 <= week <= max_week

    @staticmethod
    def validate_month(month):
        """Validate month."""

        return 1 <= month <= 12

    @staticmethod
    def validate_year(year):
        """Validate year."""

        return 1 <= year

    @staticmethod
    def validate_hour(hour):
        """Validate hour."""

        return 0 <= hour <= 23

    @staticmethod
    def validate_minutes(minutes):
        """Validate minutes."""

        return 0 <= minutes <= 59

    @classmethod
    def parse_value(cls, itype, value):
        """Parse the input value."""

        parsed = None
        if itype == "date":
            m = RE_DATE.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                day = int(m.group('day'), 10)
                if cls.validate_year(year) and cls.validate_month(month) and cls.validate_day(year, month, day):
                    parsed = (year, month, day)
        elif itype == "month":
            m = RE_MONTH.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                if cls.validate_year(year) and cls.validate_month(month):
                    parsed = (year, month)
        elif itype == "week":
            m = RE_WEEK.match(value)
            if m:
                year = int(m.group('year'), 10)
                week = int(m.group('week'), 10)
                if cls.validate_year(year) and cls.validate_week(year, week):
                    parsed = (year, week)
        elif itype == "time":
            m = RE_TIME.match(value)
            if m:
                hour = int(m.group('hour'), 10)
                minutes = int(m.group('minutes'), 10)
                if cls.validate_hour(hour) and cls.validate_minutes(minutes):
                    parsed = (hour, minutes)
        elif itype == "datetime-local":
            m = RE_DATETIME.match(value)
            if m:
                year = int(m.group('year'), 10)
                month = int(m.group('month'), 10)
                day = int(m.group('day'), 10)
                hour = int(m.group('hour'), 10)
                minutes = int(m.group('minutes'), 10)
                if (
                    cls.validate_year(year) and cls.validate_month(month) and cls.validate_day(year, month, day) and
                    cls.validate_hour(hour) and cls.validate_minutes(minutes)
                ):
                    parsed = (year, month, day, hour, minutes)
        elif itype in ("number", "range"):
            m = RE_NUM.match(value)
            if m:
                parsed = float(m.group('value'))
        return parsed


class _Match(object):
    """Perform CSS matching."""

    def __init__(self, selectors, scope, namespaces, flags):
        """Initialize."""

        self.assert_valid_input(scope)
        self.tag = scope
        self.cached_meta_lang = []
        self.cached_default_forms = []
        self.cached_indeterminate_forms = []
        self.selectors = selectors
        self.namespaces = {} if namespaces is None else namespaces
        self.flags = flags
        self.iframe_restrict = False

        # Find the root element for the whole tree
        doc = scope
        parent = self.get_parent(doc)
        while parent:
            doc = parent
            parent = self.get_parent(doc)
        root = None
        if not self.is_doc(doc):
            root = doc
        else:
            for child in self.get_children(doc):
                root = child
                break

        self.root = root
        self.scope = scope if scope is not doc else root
        self.has_html_namespace = self.has_html_ns(root)

        # A document can be both XML and HTML (XHTML)
        self.is_xml = self.is_xml_tree(doc)
        self.is_html = not self.is_xml or self.has_html_namespace

    def supports_namespaces(self):
        """Check if namespaces are supported in the HTML type."""

        return self.is_xml or self.has_html_namespace

    def get_tag_ns(self, el):
        """Get tag namespace."""

        if self.supports_namespaces():
            namespace = ''
            ns = self.get_uri(el)
            if ns:
                namespace = ns
        else:
            namespace = NS_XHTML
        return namespace

    def is_html_tag(self, el):
        """Check if tag is in HTML namespace."""

        return self.get_tag_ns(el) == NS_XHTML

    def get_tag(self, el):
        """Get tag."""

        name = self.get_tag_name(el)
        return util.lower(name) if name is not None and not self.is_xml else name

    def get_prefix(self, el):
        """Get prefix."""

        prefix = self.get_prefix_name(el)
        return util.lower(prefix) if prefix is not None and not self.is_xml else prefix

    def find_bidi(self, el):
        """Get directionality from element text."""

        for node in self.get_children(el, tags=False):

            # Analyze child text nodes
            if self.is_tag(node):

                # Avoid analyzing certain elements specified in the specification.
                direction = DIR_MAP.get(util.lower(self.get_attribute_by_name(node, 'dir', '')), None)
                if (
                    self.get_tag(node) in ('bdi', 'script', 'style', 'textarea', 'iframe') or
                    not self.is_html_tag(node) or
                    direction is not None
                ):
                    continue  # pragma: no cover

                # Check directionality of this node's text
                value = self.find_bidi(node)
                if value is not None:
                    return value

                # Direction could not be determined
                continue  # pragma: no cover

            # Skip `doctype` comments, etc.
            if self.is_special_string(node):
                continue

            # Analyze text nodes for directionality.
            for c in node:
                bidi = unicodedata.bidirectional(c)
                if bidi in ('AL', 'R', 'L'):
                    return ct.SEL_DIR_LTR if bidi == 'L' else ct.SEL_DIR_RTL
        return None

    def extended_language_filter(self, lang_range, lang_tag):
        """Filter the language tags."""

        match = True
        lang_range = RE_WILD_STRIP.sub('-', lang_range).lower()
        ranges = lang_range.split('-')
        subtags = lang_tag.lower().split('-')
        length = len(ranges)
        rindex = 0
        sindex = 0
        r = ranges[rindex]
        s = subtags[sindex]

        # Primary tag needs to match
        if r != '*' and r != s:
            match = False

        rindex += 1
        sindex += 1

        # Match until we run out of ranges
        while match and rindex < length:
            r = ranges[rindex]
            try:
                s = subtags[sindex]
            except IndexError:
                # Ran out of subtags,
                # but we still have ranges
                match = False
                continue

            # Empty range
            if not r:
                match = False
                continue

            # Matched range
            elif s == r:
                rindex += 1

            # Implicit wildcard cannot match
            # singletons
            elif len(s) == 1:
                match = False
                continue

            # Implicitly matched, so grab next subtag
            sindex += 1

        return match

    def match_attribute_name(self, el, attr, prefix):
        """Match attribute name and return value if it exists."""

        value = None
        if self.supports_namespaces():
            value = None
            # If we have not defined namespaces, we can't very well find them, so don't bother trying.
            if prefix:
                ns = self.namespaces.get(prefix)
                if ns is None and prefix != '*':
                    return None
            else:
                ns = None

            for k, v in self.iter_attributes(el):

                # Get attribute parts
                namespace, name = self.split_namespace(el, k)

                # Can't match a prefix attribute as we haven't specified one to match
                # Try to match it normally as a whole `p:a` as selector may be trying `p\:a`.
                if ns is None:
                    if (self.is_xml and attr == k) or (not self.is_xml and util.lower(attr) == util.lower(k)):
                        value = v
                        break
                    # Coverage is not finding this even though it is executed.
                    # Adding a print statement before this (and erasing coverage) causes coverage to find the line.
                    # Ignore the false positive message.
                    continue  # pragma: no cover

                # We can't match our desired prefix attribute as the attribute doesn't have a prefix
                if namespace is None or ns != namespace and prefix != '*':
                    continue

                # The attribute doesn't match.
                if (util.lower(attr) != util.lower(name)) if not self.is_xml else (attr != name):
                    continue

                value = v
                break
        else:
            for k, v in self.iter_attributes(el):
                if util.lower(attr) != util.lower(k):
                    continue
                value = v
                break
        return value

    def match_namespace(self, el, tag):
        """Match the namespace of the element."""

        match = True
        namespace = self.get_tag_ns(el)
        default_namespace = self.namespaces.get('')
        tag_ns = '' if tag.prefix is None else self.namespaces.get(tag.prefix, None)
        # We must match the default namespace if one is not provided
        if tag.prefix is None and (default_namespace is not None and namespace != default_namespace):
            match = False
        # If we specified `|tag`, we must not have a namespace.
        elif (tag.prefix is not None and tag.prefix == '' and namespace):
            match = False
        # Verify prefix matches
        elif (
            tag.prefix and
            tag.prefix != '*' and (tag_ns is None or namespace != tag_ns)
        ):
            match = False
        return match

    def match_attributes(self, el, attributes):
        """Match attributes."""

        match = True
        if attributes:
            for a in attributes:
                value = self.match_attribute_name(el, a.attribute, a.prefix)
                pattern = a.xml_type_pattern if self.is_xml and a.xml_type_pattern else a.pattern
                if isinstance(value, list):
                    value = ' '.join(value)
                if value is None:
                    match = False
                    break
                elif pattern is None:
                    continue
                elif pattern.match(value) is None:
                    match = False
                    break
        return match

    def match_tagname(self, el, tag):
        """Match tag name."""

        name = (util.lower(tag.name) if not self.is_xml and tag.name is not None else tag.name)
        return not (
            name is not None and
            name not in (self.get_tag(el), '*')
        )

    def match_tag(self, el, tag):
        """Match the tag."""

        match = True
        if tag is not None:
            # Verify namespace
            if not self.match_namespace(el, tag):
                match = False
            if not self.match_tagname(el, tag):
                match = False
        return match

    def match_past_relations(self, el, relation):
        """Match past relationship."""

        found = False
        if relation[0].rel_type == REL_PARENT:
            parent = self.get_parent(el, no_iframe=self.iframe_restrict)
            while not found and parent:
                found = self.match_selectors(parent, relation)
                parent = self.get_parent(parent, no_iframe=self.iframe_restrict)
        elif relation[0].rel_type == REL_CLOSE_PARENT:
            parent = self.get_parent(el, no_iframe=self.iframe_restrict)
            if parent:
                found = self.match_selectors(parent, relation)
        elif relation[0].rel_type == REL_SIBLING:
            sibling = self.get_previous(el)
            while not found and sibling:
                found = self.match_selectors(sibling, relation)
                sibling = self.get_previous(sibling)
        elif relation[0].rel_type == REL_CLOSE_SIBLING:
            sibling = self.get_previous(el)
            if sibling and self.is_tag(sibling):
                found = self.match_selectors(sibling, relation)
        return found

    def match_future_child(self, parent, relation, recursive=False):
        """Match future child."""

        match = False
        children = self.get_descendants if recursive else self.get_children
        for child in children(parent, no_iframe=self.iframe_restrict):
            match = self.match_selectors(child, relation)
            if match:
                break
        return match

    def match_future_relations(self, el, relation):
        """Match future relationship."""

        found = False
        if relation[0].rel_type == REL_HAS_PARENT:
            found = self.match_future_child(el, relation, True)
        elif relation[0].rel_type == REL_HAS_CLOSE_PARENT:
            found = self.match_future_child(el, relation)
        elif relation[0].rel_type == REL_HAS_SIBLING:
            sibling = self.get_next(el)
            while not found and sibling:
                found = self.match_selectors(sibling, relation)
                sibling = self.get_next(sibling)
        elif relation[0].rel_type == REL_HAS_CLOSE_SIBLING:
            sibling = self.get_next(el)
            if sibling and self.is_tag(sibling):
                found = self.match_selectors(sibling, relation)
        return found

    def match_relations(self, el, relation):
        """Match relationship to other elements."""

        found = False

        if relation[0].rel_type.startswith(':'):
            found = self.match_future_relations(el, relation)
        else:
            found = self.match_past_relations(el, relation)

        return found

    def match_id(self, el, ids):
        """Match element's ID."""

        found = True
        for i in ids:
            if i != self.get_attribute_by_name(el, 'id', ''):
                found = False
                break
        return found

    def match_classes(self, el, classes):
        """Match element's classes."""

        current_classes = self.get_classes(el)
        found = True
        for c in classes:
            if c not in current_classes:
                found = False
                break
        return found

    def match_root(self, el):
        """Match element as root."""

        is_root = self.is_root(el)
        if is_root:
            sibling = self.get_previous(el, tags=False)
            while is_root and sibling is not None:
                if (
                    self.is_tag(sibling) or (self.is_content_string(sibling) and sibling.strip()) or
                    self.is_cdata(sibling)
                ):
                    is_root = False
                else:
                    sibling = self.get_previous(sibling, tags=False)
        if is_root:
            sibling = self.get_next(el, tags=False)
            while is_root and sibling is not None:
                if (
                    self.is_tag(sibling) or (self.is_content_string(sibling) and sibling.strip()) or
                    self.is_cdata(sibling)
                ):
                    is_root = False
                else:
                    sibling = self.get_next(sibling, tags=False)
        return is_root

    def match_scope(self, el):
        """Match element as scope."""

        return self.scope is el

    def match_nth_tag_type(self, el, child):
        """Match tag type for `nth` matches."""

        return(
            (self.get_tag(child) == self.get_tag(el)) and
            (self.get_tag_ns(child) == self.get_tag_ns(el))
        )

    def match_nth(self, el, nth):
        """Match `nth` elements."""

        matched = True

        for n in nth:
            matched = False
            if n.selectors and not self.match_selectors(el, n.selectors):
                break
            parent = self.get_parent(el)
            if parent is None:
                parent = self.create_fake_parent(el)
            last = n.last
            last_index = len(parent) - 1
            index = last_index if last else 0
            relative_index = 0
            a = n.a
            b = n.b
            var = n.n
            count = 0
            count_incr = 1
            factor = -1 if last else 1
            idx = last_idx = a * count + b if var else a

            # We can only adjust bounds within a variable index
            if var:
                # Abort if our nth index is out of bounds and only getting further out of bounds as we increment.
                # Otherwise, increment to try to get in bounds.
                adjust = None
                while idx < 1 or idx > last_index:
                    if idx < 0:
                        diff_low = 0 - idx
                        if adjust is not None and adjust == 1:
                            break
                        adjust = -1
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                        diff = 0 - idx
                        if diff >= diff_low:
                            break
                    else:
                        diff_high = idx - last_index
                        if adjust is not None and adjust == -1:
                            break
                        adjust = 1
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                        diff = idx - last_index
                        if diff >= diff_high:
                            break
                        diff_high = diff

                # If a < 0, our count is working backwards, so floor the index by increasing the count.
                # Find the count that yields the lowest, in bound value and use that.
                # Lastly reverse count increment so that we'll increase our index.
                lowest = count
                if a < 0:
                    while idx >= 1:
                        lowest = count
                        count += count_incr
                        idx = last_idx = a * count + b if var else a
                    count_incr = -1
                count = lowest
                idx = last_idx = a * count + b if var else a

            # Evaluate elements while our calculated nth index is still in range
            while 1 <= idx <= last_index + 1:
                child = None
                # Evaluate while our child index is still in range.
                for child in self.get_children(parent, start=index, reverse=factor < 0, tags=False):
                    index += factor
                    if not self.is_tag(child):
                        continue
                    # Handle `of S` in `nth-child`
                    if n.selectors and not self.match_selectors(child, n.selectors):
                        continue
                    # Handle `of-type`
                    if n.of_type and not self.match_nth_tag_type(el, child):
                        continue
                    relative_index += 1
                    if relative_index == idx:
                        if child is el:
                            matched = True
                        else:
                            break
                    if child is el:
                        break
                if child is el:
                    break
                last_idx = idx
                count += count_incr
                if count < 0:
                    # Count is counting down and has now ventured into invalid territory.
                    break
                idx = a * count + b if var else a
                if last_idx == idx:
                    break
            if not matched:
                break
        return matched

    def match_empty(self, el):
        """Check if element is empty (if requested)."""

        is_empty = True
        for child in self.get_children(el, tags=False):
            if self.is_tag(child):
                is_empty = False
                break
            elif self.is_content_string(child) and RE_NOT_EMPTY.search(child):
                is_empty = False
                break
        return is_empty

    def match_subselectors(self, el, selectors):
        """Match selectors."""

        match = True
        for sel in selectors:
            if not self.match_selectors(el, sel):
                match = False
        return match

    def match_contains(self, el, contains):
        """Match element if it contains text."""

        match = True
        content = None
        for contain_list in contains:
            if content is None:
                content = self.get_text(el, no_iframe=self.is_html)
            found = False
            for text in contain_list.text:
                if text in content:
                    found = True
                    break
            if not found:
                match = False
        return match

    def match_default(self, el):
        """Match default."""

        match = False

        # Find this input's form
        form = None
        parent = self.get_parent(el, no_iframe=True)
        while parent and form is None:
            if self.get_tag(parent) == 'form' and self.is_html_tag(parent):
                form = parent
            else:
                parent = self.get_parent(parent, no_iframe=True)

        # Look in form cache to see if we've already located its default button
        found_form = False
        for f, t in self.cached_default_forms:
            if f is form:
                found_form = True
                if t is el:
                    match = True
                break

        # We didn't have the form cached, so look for its default button
        if not found_form:
            for child in self.get_descendants(form, no_iframe=True):
                name = self.get_tag(child)
                # Can't do nested forms (haven't figured out why we never hit this)
                if name == 'form':  # pragma: no cover
                    break
                if name in ('input', 'button'):
                    v = self.get_attribute_by_name(child, 'type', '')
                    if v and util.lower(v) == 'submit':
                        self.cached_default_forms.append([form, child])
                        if el is child:
                            match = True
                        break
        return match

    def match_indeterminate(self, el):
        """Match default."""

        match = False
        name = self.get_attribute_by_name(el, 'name')

        def get_parent_form(el):
            """Find this input's form."""
            form = None
            parent = self.get_parent(el, no_iframe=True)
            while form is None:
                if self.get_tag(parent) == 'form' and self.is_html_tag(parent):
                    form = parent
                    break
                last_parent = parent
                parent = self.get_parent(parent, no_iframe=True)
                if parent is None:
                    form = last_parent
                    break
            return form

        form = get_parent_form(el)

        # Look in form cache to see if we've already evaluated that its fellow radio buttons are indeterminate
        found_form = False
        for f, n, i in self.cached_indeterminate_forms:
            if f is form and n == name:
                found_form = True
                if i is True:
                    match = True
                break

        # We didn't have the form cached, so validate that the radio button is indeterminate
        if not found_form:
            checked = False
            for child in self.get_descendants(form, no_iframe=True):
                if child is el:
                    continue
                tag_name = self.get_tag(child)
                if tag_name == 'input':
                    is_radio = False
                    check = False
                    has_name = False
                    for k, v in self.iter_attributes(child):
                        if util.lower(k) == 'type' and util.lower(v) == 'radio':
                            is_radio = True
                        elif util.lower(k) == 'name' and v == name:
                            has_name = True
                        elif util.lower(k) == 'checked':
                            check = True
                        if is_radio and check and has_name and get_parent_form(child) is form:
                            checked = True
                            break
                if checked:
                    break
            if not checked:
                match = True
            self.cached_indeterminate_forms.append([form, name, match])

        return match

    def match_lang(self, el, langs):
        """Match languages."""

        match = False
        has_ns = self.supports_namespaces()
        root = self.root
        has_html_namespace = self.has_html_namespace

        # Walk parents looking for `lang` (HTML) or `xml:lang` XML property.
        parent = el
        found_lang = None
        last = None
        while not found_lang:
            has_html_ns = self.has_html_ns(parent)
            for k, v in self.iter_attributes(parent):
                attr_ns, attr = self.split_namespace(parent, k)
                if (
                    ((not has_ns or has_html_ns) and (util.lower(k) if not self.is_xml else k) == 'lang') or
                    (
                        has_ns and not has_html_ns and attr_ns == NS_XML and
                        (util.lower(attr) if not self.is_xml and attr is not None else attr) == 'lang'
                    )
                ):
                    found_lang = v
                    break
            last = parent
            parent = self.get_parent(parent, no_iframe=self.is_html)

            if parent is None:
                root = last
                has_html_namespace = self.has_html_ns(root)
                parent = last
                break

        # Use cached meta language.
        if not found_lang and self.cached_meta_lang:
            for cache in self.cached_meta_lang:
                if root is cache[0]:
                    found_lang = cache[1]

        # If we couldn't find a language, and the document is HTML, look to meta to determine language.
        if found_lang is None and (not self.is_xml or (has_html_namespace and root.name == 'html')):
            # Find head
            found = False
            for tag in ('html', 'head'):
                found = False
                for child in self.get_children(parent, no_iframe=self.is_html):
                    if self.get_tag(child) == tag and self.is_html_tag(child):
                        found = True
                        parent = child
                        break
                if not found:  # pragma: no cover
                    break

            # Search meta tags
            if found:
                for child in parent:
                    if self.is_tag(child) and self.get_tag(child) == 'meta' and self.is_html_tag(parent):
                        c_lang = False
                        content = None
                        for k, v in self.iter_attributes(child):
                            if util.lower(k) == 'http-equiv' and util.lower(v) == 'content-language':
                                c_lang = True
                            if util.lower(k) == 'content':
                                content = v
                            if c_lang and content:
                                found_lang = content
                                self.cached_meta_lang.append((root, found_lang))
                                break
                    if found_lang:
                        break
                if not found_lang:
                    self.cached_meta_lang.append((root, False))

        # If we determined a language, compare.
        if found_lang:
            for patterns in langs:
                match = False
                for pattern in patterns:
                    if self.extended_language_filter(pattern, found_lang):
                        match = True
                if not match:
                    break

        return match

    def match_dir(self, el, directionality):
        """Check directionality."""

        # If we have to match both left and right, we can't match either.
        if directionality & ct.SEL_DIR_LTR and directionality & ct.SEL_DIR_RTL:
            return False

        if el is None or not self.is_html_tag(el):
            return False

        # Element has defined direction of left to right or right to left
        direction = DIR_MAP.get(util.lower(self.get_attribute_by_name(el, 'dir', '')), None)
        if direction not in (None, 0):
            return direction == directionality

        # Element is the document element (the root) and no direction assigned, assume left to right.
        is_root = self.is_root(el)
        if is_root and direction is None:
            return ct.SEL_DIR_LTR == directionality

        # If `input[type=telephone]` and no direction is assigned, assume left to right.
        name = self.get_tag(el)
        is_input = name == 'input'
        is_textarea = name == 'textarea'
        is_bdi = name == 'bdi'
        itype = util.lower(self.get_attribute_by_name(el, 'type', '')) if is_input else ''
        if is_input and itype == 'tel' and direction is None:
            return ct.SEL_DIR_LTR == directionality

        # Auto handling for text inputs
        if ((is_input and itype in ('text', 'search', 'tel', 'url', 'email')) or is_textarea) and direction == 0:
            if is_textarea:
                value = []
                for node in self.get_contents(el, no_iframe=True):
                    if self.is_content_string(node):
                        value.append(node)
                value = ''.join(value)
            else:
                value = self.get_attribute_by_name(el, 'value', '')
            if value:
                for c in value:
                    bidi = unicodedata.bidirectional(c)
                    if bidi in ('AL', 'R', 'L'):
                        direction = ct.SEL_DIR_LTR if bidi == 'L' else ct.SEL_DIR_RTL
                        return direction == directionality
                # Assume left to right
                return ct.SEL_DIR_LTR == directionality
            elif is_root:
                return ct.SEL_DIR_LTR == directionality
            return self.match_dir(self.get_parent(el, no_iframe=True), directionality)

        # Auto handling for `bdi` and other non text inputs.
        if (is_bdi and direction is None) or direction == 0:
            direction = self.find_bidi(el)
            if direction is not None:
                return direction == directionality
            elif is_root:
                return ct.SEL_DIR_LTR == directionality
            return self.match_dir(self.get_parent(el, no_iframe=True), directionality)

        # Match parents direction
        return self.match_dir(self.get_parent(el, no_iframe=True), directionality)

    def match_range(self, el, condition):
        """
        Match range.

        Behavior is modeled after what we see in browsers. Browsers seem to evaluate
        if the value is out of range, and if not, it is in range. So a missing value
        will not evaluate out of range; therefore, value is in range. Personally, I
        feel like this should evaluate as neither in or out of range.
        """

        out_of_range = False

        itype = util.lower(self.get_attribute_by_name(el, 'type'))
        mn = self.get_attribute_by_name(el, 'min', None)
        if mn is not None:
            mn = Inputs.parse_value(itype, mn)
        mx = self.get_attribute_by_name(el, 'max', None)
        if mx is not None:
            mx = Inputs.parse_value(itype, mx)

        # There is no valid min or max, so we cannot evaluate a range
        if mn is None and mx is None:
            return False

        value = self.get_attribute_by_name(el, 'value', None)
        if value is not None:
            value = Inputs.parse_value(itype, value)
        if value is not None:
            if itype in ("date", "datetime-local", "month", "week", "number", "range"):
                if mn is not None and value < mn:
                    out_of_range = True
                if not out_of_range and mx is not None and value > mx:
                    out_of_range = True
            elif itype == "time":
                if mn is not None and mx is not None and mn > mx:
                    # Time is periodic, so this is a reversed/discontinuous range
                    if value < mn and value > mx:
                        out_of_range = True
                else:
                    if mn is not None and value < mn:
                        out_of_range = True
                    if not out_of_range and mx is not None and value > mx:
                        out_of_range = True

        return not out_of_range if condition & ct.SEL_IN_RANGE else out_of_range

    def match_defined(self, el):
        """
        Match defined.

        `:defined` is related to custom elements in a browser.

        - If the document is XML (not XHTML), all tags will match.
        - Tags that are not custom (don't have a hyphen) are marked defined.
        - If the tag has a prefix (without or without a namespace), it will not match.

        This is of course requires the parser to provide us with the proper prefix and namespace info,
        if it doesn't, there is nothing we can do.
        """

        name = self.get_tag(el)
        return (
            name.find('-') == -1 or
            name.find(':') != -1 or
            self.get_prefix(el) is not None
        )

    def match_placeholder_shown(self, el):
        """
        Match placeholder shown according to HTML spec.

        - text area should be checked if they have content. A single newline does not count as content.

        """

        match = False
        content = self.get_text(el)
        if content in ('', '\n'):
            match = True

        return match

    def match_selectors(self, el, selectors):
        """Check if element matches one of the selectors."""

        match = False
        is_not = selectors.is_not
        is_html = selectors.is_html

        # Internal selector lists that use the HTML flag, will automatically get the `html` namespace.
        if is_html:
            namespaces = self.namespaces
            iframe_restrict = self.iframe_restrict
            self.namespaces = {'html': NS_XHTML}
            self.iframe_restrict = True

        if not is_html or self.is_html:
            for selector in selectors:
                match = is_not
                # We have a un-matchable situation (like `:focus` as you can focus an element in this environment)
                if isinstance(selector, ct.SelectorNull):
                    continue
                # Verify tag matches
                if not self.match_tag(el, selector.tag):
                    continue
                # Verify tag is defined
                if selector.flags & ct.SEL_DEFINED and not self.match_defined(el):
                    continue
                # Verify element is root
                if selector.flags & ct.SEL_ROOT and not self.match_root(el):
                    continue
                # Verify element is scope
                if selector.flags & ct.SEL_SCOPE and not self.match_scope(el):
                    continue
                # Verify element has placeholder shown
                if selector.flags & ct.SEL_PLACEHOLDER_SHOWN and not self.match_placeholder_shown(el):
                    continue
                # Verify `nth` matches
                if not self.match_nth(el, selector.nth):
                    continue
                if selector.flags & ct.SEL_EMPTY and not self.match_empty(el):
                    continue
                # Verify id matches
                if selector.ids and not self.match_id(el, selector.ids):
                    continue
                # Verify classes match
                if selector.classes and not self.match_classes(el, selector.classes):
                    continue
                # Verify attribute(s) match
                if not self.match_attributes(el, selector.attributes):
                    continue
                # Verify ranges
                if selector.flags & RANGES and not self.match_range(el, selector.flags & RANGES):
                    continue
                # Verify language patterns
                if selector.lang and not self.match_lang(el, selector.lang):
                    continue
                # Verify pseudo selector patterns
                if selector.selectors and not self.match_subselectors(el, selector.selectors):
                    continue
                # Verify relationship selectors
                if selector.relation and not self.match_relations(el, selector.relation):
                    continue
                # Validate that the current default selector match corresponds to the first submit button in the form
                if selector.flags & ct.SEL_DEFAULT and not self.match_default(el):
                    continue
                # Validate that the unset radio button is among radio buttons with the same name in a form that are
                # also not set.
                if selector.flags & ct.SEL_INDETERMINATE and not self.match_indeterminate(el):
                    continue
                # Validate element directionality
                if selector.flags & DIR_FLAGS and not self.match_dir(el, selector.flags & DIR_FLAGS):
                    continue
                # Validate that the tag contains the specified text.
                if not self.match_contains(el, selector.contains):
                    continue
                match = not is_not
                break

        # Restore actual namespaces being used for external selector lists
        if is_html:
            self.namespaces = namespaces
            self.iframe_restrict = iframe_restrict

        return match

    def select(self, limit=0):
        """Match all tags under the targeted tag."""

        if limit < 1:
            limit = None

        for child in self.get_descendants(self.tag):
            if self.match(child):
                yield child
                if limit is not None:
                    limit -= 1
                    if limit < 1:
                        break

    def closest(self):
        """Match closest ancestor."""

        current = self.tag
        closest = None
        while closest is None and current is not None:
            if self.match(current):
                closest = current
            else:
                current = self.get_parent(current)
        return closest

    def filter(self):  # noqa A001
        """Filter tag's children."""

        return [tag for tag in self.get_contents(self.tag) if not self.is_navigable_string(tag) and self.match(tag)]

    def match(self, el):
        """Match."""

        return not self.is_doc(el) and self.is_tag(el) and self.match_selectors(el, self.selectors)


class CSSMatch(_DocumentNav, _Match):
    """The Beautiful Soup CSS match class."""


class SoupSieve(ct.Immutable):
    """Compiled Soup Sieve selector matching object."""

    __slots__ = ("pattern", "selectors", "namespaces", "custom", "flags", "_hash")

    def __init__(self, pattern, selectors, namespaces, custom, flags):
        """Initialize."""

        super(SoupSieve, self).__init__(
            pattern=pattern,
            selectors=selectors,
            namespaces=namespaces,
            custom=custom,
            flags=flags
        )

    def match(self, tag):
        """Match."""

        return CSSMatch(self.selectors, tag, self.namespaces, self.flags).match(tag)

    def closest(self, tag):
        """Match closest ancestor."""

        return CSSMatch(self.selectors, tag, self.namespaces, self.flags).closest()

    def filter(self, iterable):  # noqa A001
        """
        Filter.

        `CSSMatch` can cache certain searches for tags of the same document,
        so if we are given a tag, all tags are from the same document,
        and we can take advantage of the optimization.

        Any other kind of iterable could have tags from different documents or detached tags,
        so for those, we use a new `CSSMatch` for each item in the iterable.
        """

        if CSSMatch.is_tag(iterable):
            return CSSMatch(self.selectors, iterable, self.namespaces, self.flags).filter()
        else:
            return [node for node in iterable if not CSSMatch.is_navigable_string(node) and self.match(node)]

    def select_one(self, tag):
        """Select a single tag."""

        tags = self.select(tag, limit=1)
        return tags[0] if tags else None

    def select(self, tag, limit=0):
        """Select the specified tags."""

        return list(self.iselect(tag, limit))

    def iselect(self, tag, limit=0):
        """Iterate the specified tags."""

        for el in CSSMatch(self.selectors, tag, self.namespaces, self.flags).select(limit):
            yield el

    def __repr__(self):  # pragma: no cover
        """Representation."""

        return "SoupSieve(pattern={!r}, namespaces={!r}, custom={!r}, flags={!r})".format(
            self.pattern,
            self.namespaces,
            self.custom,
            self.flags
        )

    __str__ = __repr__


ct.pickle_register(SoupSieve)
