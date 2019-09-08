"""
LaTex generator methods.
"""
from gramps.gen.plug.docgen import BaseDoc, TextDoc
from gramps.gen.plug.docbackend import DocBackend

class LaTeXDoc(BaseDoc, TextDoc):
    """
    Document method handler.
    """

    def __init__(self, styles, paper_style, track, uistate=None):
        BaseDoc.__init__(self, styles, paper_style, track, uistate)
        self._backend = None
        self._table_cells = []
        self._collect_cells = False
        self._open_cell = None

    def open(self, filename):
        """Opens the specified file, making sure that it has the
        extension of .tex"""
        self._backend = LaTeXBackend(filename)
        self._backend.open()
        self._backend.write(
            r"\documentclass[a4paper,landscape]{article}" + "\n")
        self._backend.write(r"\usepackage[a4paper,landscape]{geometry}" + "\n")
        self._backend.write(r"\usepackage{genealogytree}" + "\n")
        self._backend.write(r"\begin{document}" + "\n")
        self._backend.write(r"\begin{center}" + "\n")

    def close(self):
        """Clean up and close the document"""
        self._backend.write(r"\end{center}" + "\n")
        self._backend.write(r"\end{document}")
        self._backend.close()

    def write_text(self, text, mark=None, links=False):
        """Write the text to the file"""
        if self._open_cell is None:
            self._backend.write(text)
        else:
            self._open_cell = (self._open_cell[0] + text, self._open_cell[1])

    def start_paragraph(self, style_name, leader=None):
        """Paragraphs handling - A Gramps paragraph is any
        single body of text from a single word to several sentences.
        We assume a linebreak at the end of each paragraph."""

    def end_paragraph(self):
        """End the current paragraph"""
        pass

    def start_bold(self):
        """Bold face"""
        pass

    def end_bold(self):
        """End bold face"""
        pass

    def start_table(self, name, style_name):
        """Begin new table"""
        self._backend.write(r"\begin{table}" + "\n")
        self._backend.write(
            r"\begin{tabular}{l r r l c r r l c r r l l c l}" + "\n")

    def end_table(self):
        """Close the table environment"""
        self._backend.write(r"\end{tabular}" + "\n")
        self._backend.write(r"\\\\\noindent\rule[0.5ex]{\linewidth}{1pt}" + "\n")
        self._backend.write(r"\end{table}" + "\n")

    def start_row(self):
        """Begin a new row"""
        self._table_cells = []

    def end_row(self):
        """End the row (new line)"""
        self._backend.write("&".join(self._table_cells))

        self._backend.write(r"\\" + "\n")

    def start_cell(self, style_name, span=1):
        """Add an entry to the table.
        We always place our data inside braces
        for safety of formatting."""
        self._open_cell = ("", 1)
        if span > 1:
            self._open_cell = (r"\multicolumn{" + \
                               "{}".format(span) + r"}{c}{", span)

    def end_cell(self):
        """Prepares for next cell"""
        if self._open_cell[1] > 1:
            self._open_cell = (self._open_cell[0] + r"}", self._open_cell[1])
        self._table_cells.append(self._open_cell[0])
        self._open_cell = None

    def start_superscript(self):
        """Start superscript"""
        pass

    def end_superscript(self):
        """End superscript"""
        pass

    def add_media(self, name, align, w_cm, h_cm, alt='',
                  style_name=None, crop=None):
        """Add photo to report"""
        pass

    def page_break(self):
        "Forces a page break, creating a new page"
        self._backend.write(r"\newpage")

class LaTeXBackend(DocBackend):
    """
    Implementation of docbackend for latex docs.
    File and File format management for latex docs
    """
        
