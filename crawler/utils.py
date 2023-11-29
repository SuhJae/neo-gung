from bs4 import BeautifulSoup, NavigableString
import re


def is_table_otherwise_empty(table):
    """
    Check if a table contains only one image and no other significant content.
    """
    if not table:
        return False

    text_content = table.get_text(strip=True)
    if text_content:
        return False  # The table has text content

    non_empty_tags = [tag for tag in table.find_all(True) if tag.name not in ['img', 'tr', 'td', 'tbody']]
    if non_empty_tags:
        return False  # The table has other non-empty tags

    return True


class HTMLCleaner:
    def __init__(self):
        self.soup = None

    def set_soup(self, html_content):
        """Set the soup object from HTML content."""
        self.soup = BeautifulSoup(html_content, 'html.parser')

    def html_to_text(self, html_content: str) -> str:
        """
        Extracts only the text from the HTML content.
        :param html_content: HTML content to extract text from.
        :return: Extracted text.
        """
        self.set_soup(html_content)
        return self.soup.get_text()

    def merge_formatting_tags(self, soup):
        """
        Merge adjacent formatting tags (like <b>, <i>, <strong>, etc.) if they are redundant.
        """
        for tag in soup.find_all(['b', 'i', 'strong', 'em']):  # Add more tags if needed
            next_sibling = tag.find_next_sibling()
            if next_sibling and tag.name == next_sibling.name and tag.attrs == next_sibling.attrs:
                tag.string = (tag.string or '') + (next_sibling.string or '')
                next_sibling.decompose()
                # Recursively check for further adjacent tags
                self.merge_formatting_tags(soup)

    def merge_with_next_sibling(self, tag):
        """
        Merge a tag with its next sibling if they are of the same type and have the same attributes.
        """
        next_sibling = tag.next_sibling
        while next_sibling and isinstance(next_sibling, NavigableString) and not next_sibling.strip():
            next_sibling = next_sibling.next_sibling

        if next_sibling and tag.name == next_sibling.name and tag.attrs == next_sibling.attrs:
            tag.string = (tag.get_text() or '') + (next_sibling.get_text() or '')
            next_sibling.decompose()
            self.merge_with_next_sibling(tag)  # Check again in case there are more than two adjacent tags

    def remove_empty_tags(self):
        """
        Remove empty tags from the soup.
        """
        if hasattr(self, 'soup'):
            for tag in self.soup.find_all():
                # check if there are no images or line as a child
                if tag.find_all(['img', 'br']):
                    break
                # check if there are no text as a child
                if tag.name not in ['img', 'br']:
                    # check for empty tags
                    if not tag.get_text(strip=True):
                        tag.decompose()
                    # check for zero width space
                    if tag.get_text(strip=True) == '\u200b':
                        tag.decompose()
        else:
            raise AttributeError("Soup object not found in class instance.")

    def extract_single_image_from_tables(self):
        """
        Extract and replace tables that contain only a single image tag with that image tag.
        """
        if hasattr(self, 'soup'):
            tables = self.soup.find_all('table')
            for table in tables:
                images = table.find_all('img')
                if len(images) == 1 and is_table_otherwise_empty(table):
                    table.replace_with(images[0])

    def simplify_tag_stacking(self):
        """
        Simplify identical nested tags.
        For example, <b><b>text</b></b> becomes <b>text</b>.
        """

        # Recursively simplify tags in the soup
        def simplify_tag(tag):
            for child in tag.contents:
                if not isinstance(child, NavigableString):
                    simplify_tag(child)

                    # Check if the child tag is the same as the parent tag
                    if child.name == tag.name:
                        child.unwrap()

        for tag in self.soup.find_all(True):  # Find all tags
            simplify_tag(tag)

    def clean_html(self, html_content, origin) -> str:
        self.soup = BeautifulSoup(html_content, 'html.parser')

        # Remove scripts, styles, and non-essential attributes
        [tag.decompose() for tag in self.soup(['script', 'style'])]

        # Remove or unwrap unnecessary tags and attributes
        for tag in self.soup.find_all():
            if tag.name == 'a':
                if tag.get('href').startswith('http'):
                    # Just keep the href attribute for 'a' tags and open in new tab
                    tag.attrs = {'href': tag.get('href'), 'target': '_blank'}
                else:
                    # Add the origin to the href attribute for 'a' tags
                    tag.attrs = {'href': origin + tag.get('href'), 'target': '_blank'}
            elif tag.name == 'img':
                # check the src has http or https
                if tag.get('src').startswith('http'):
                    # Just keep the src and alt attributes
                    tag.attrs = {'src': tag.get('src'), 'alt': tag.get('alt')}
                else:
                    # Add the origin to the src and alt attributes
                    tag.attrs = {'src': origin + tag.get('src'), 'alt': tag.get('alt')}
            else:
                tag.attrs = {}

        # Unwrap or decompose div tags
        for div in self.soup.find_all('div'):
            div.unwrap()  # or div.decompose() to completely remove div and its content

        # Remove spans by unwrapping them
        for span in self.soup.find_all('span'):
            span.unwrap()

        self.merge_formatting_tags(self.soup)
        self.extract_single_image_from_tables()
        self.remove_empty_tags()
        self.simplify_tag_stacking()

        # Prepare minimal HTML structure
        minimal_html = self.soup.new_tag('html')
        head = self.soup.new_tag('head')
        meta = self.soup.new_tag('meta', charset='UTF-8')
        head.append(meta)
        minimal_html.append(head)
        body = self.soup.new_tag('body')
        body.append(self.soup)
        minimal_html.append(body)

        # Convert to string
        result_html = str(minimal_html)
        # normalize spaces using regex
        result_html = re.sub(r"\s+", " ", result_html)
        # remove comments
        result_html = re.sub(r"<!--.*?-->", "", result_html)

        return result_html
