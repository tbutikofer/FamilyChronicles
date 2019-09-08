import unittest
import os

from gramps.gen.const import DATA_DIR
from gramps.gen.db.utils import import_as_dict
from gramps.gen.user import User
from gramps.gen.plug import BasePluginManager
from gramps.gen.plug.docgen import StyleSheet
from gramps.gen.plug.docgen import PaperSize, PaperStyle, PAPER_LANDSCAPE

# from gramps.plugins.docgen import LaTeXDoc

from .FamilyChronicles import FamilyChronicles, FamilyChroniclesOptions
from .LaTeXDoc import LaTeXDoc

TEST_DIR = os.path.abspath(os.path.join(DATA_DIR, "tests"))
# TEST_DATA = os.path.join(TEST_DIR, "data.gramps")
TEST_DATA = "/Users/tommy/Documents/Familie/Adliken/Adliken.gramps"
PLUGMAN = BasePluginManager.get_instance()

class test_Familychroniclesmethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = import_as_dict(TEST_DATA, User())
        # pdata = PLUGMAN.get_plugin('latexdoc')
        # self.doc_class = PLUGMAN.load_plugin(pdata).LaTeXDoc
        cls.doc_class = LaTeXDoc

    @classmethod
    def tearDownClass(cls):
        pass

    def test_report(self):
        styles = StyleSheet()
        options = FamilyChroniclesOptions("Familiy Chronicles", self.db)
        options.load_previous_values()
        options.make_default_style(styles)
        paper_layout = PaperStyle(PaperSize("a4", None, None), PAPER_LANDSCAPE)
        doc = self.doc_class(styles, paper_layout, [])
        options.set_document(doc)

        options.menu.get_option_by_name('pid').set_value("I0061")

        # report = FamilyChronicles(self.db, self.options, User())
        report = FamilyChronicles(self.db, options, User())
        doc.open('testgramps.tex')
        # report.write_report()
        report.write_report()
        doc.close()

if __name__ == '__main__':
    unittest.main()
