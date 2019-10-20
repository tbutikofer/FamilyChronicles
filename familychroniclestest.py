""" Unittest methods for FamilyChronicles report """
import unittest
from unittest.mock import Mock

from gramps.gen.db.utils import import_as_dict
from gramps.gen.plug import BasePluginManager
from gramps.gen.plug.docgen import PaperSize, PaperStyle, PAPER_LANDSCAPE
from gramps.gen.plug.docgen import StyleSheet
from gramps.gen.user import User
from gramps.gen.dbstate import DbState
from gramps.gui.plug.report._textreportdialog import TextReportDialog
from gramps.gui.pluginmanager import GuiPluginManager

from .familychronicles import FamilyChronicles, FamilyChroniclesOptions

PLUGMAN = BasePluginManager.get_instance()
# TEST_INPUT = '/Users/tommy/Documents/Familie/Adliken/Adliken.gramps'
TEST_INPUT = '/Users/tommy/Documents/Familie/gramps/Bütikofer-2019-10-20-21-35-08.gramps'
TEST_OUTPUT = '/Users/tommy/Documents/Familie/gramps/FamilyChroniclesTest.tex'
TEST_PERSON_ID = 'I1907'
USER_PLUGIN_DIR = '/Users/tommy/Library/Application Support/gramps/gramps51/plugins'

class Familychroniclestest(unittest.TestCase):
#class Test_Familychroniclesmethods(unittest.TestCase):
    """ Unittest methods for FamilyChronicles report """

    @classmethod
    def setUpClass(cls):
        """ Import test data as in-memory database """
        cls.db = import_as_dict(TEST_INPUT, User())

    @classmethod
    def tearDownClass(cls):
        """ Close database """
        cls.db.close()

    @staticmethod
    def __get_docgen_plugin(plugin_id):
        docgen_plugin = None
        for plugin in PLUGMAN.get_docgen_plugins():
            if plugin.get_module_name() == plugin_id:
                docgen_plugin = plugin
                break
        return docgen_plugin

    @staticmethod
    def __get_user_report(report_id):
        PLUGMAN.reg_plugins(USER_PLUGIN_DIR)
        found_pdata = None
        for pdata in PLUGMAN.get_reg_reports():
            if pdata.id == report_id:
                found_pdata = pdata
                break
        return found_pdata

    @classmethod
    def __mock_uistate(cls, pid):
        active_person = cls.db.get_person_from_gramps_id(pid)
        uistate = Mock()
        uistate.gwm.get_item_from_id.return_value = None
        uistate.gwm.add_item.return_value = []
        uistate.window = None
        uistate.get_active.return_value = active_person.handle
        uistate.gwm.find_modal_window.return_value = None
        return uistate

    def test_write_report(self):
        """
        Creates a report from test data.
        """
        options = FamilyChroniclesOptions("Familiy Chronicles", self.db)
        options.load_previous_values()
        options.menu.get_option_by_name('pid').set_value(TEST_PERSON_ID)

        docgen_plugin = Familychroniclestest.__get_docgen_plugin('latexdoc')
        doc_class = docgen_plugin.get_basedoc()

        styles = StyleSheet()
        options.make_default_style(styles)
        paper_layout = PaperStyle(PaperSize("a4", None, None), PAPER_LANDSCAPE)
        doc = doc_class(styles, paper_layout, [])
        options.set_document(doc)
        options.set_output(TEST_OUTPUT)

        # Initialization sequence inspired by _reportdialog.py, report()
        my_report = FamilyChronicles(self.db, options, User())
        my_report.doc.init()
        my_report.begin_report()
        my_report.write_report()
        my_report.end_report()

    def test_dialog(self):
        """
        Tests report dialog integration
        """
        uistate = Familychroniclestest.__mock_uistate(TEST_PERSON_ID)
        dbstate = DbState()
        dbstate.change_database_noclose(self.db)
        TextReportDialog(dbstate, uistate, FamilyChroniclesOptions, "Familiy Chronicles", None)

    def test_load_plugin(self):
        pdata = Familychroniclestest.__get_user_report('FamilyChronicles')
        pmgr = GuiPluginManager.get_instance()
        module = pmgr.load_plugin(pdata)
        assert module is not None

    def test_get_families(self):
        families = {}
        i = 0
        for person_ref in self.db.get_person_handles():
            person = self.db.get_person_from_handle(person_ref)
            name = person.get_primary_name()
            first_name = name.first_name
            surname = name.get_surname()
            if surname == 'Bütikofer':
                family_id = self._get_top_family(person, None)
                if family_id not in families:
                    families[family_id] = 1
                else:
                    families[family_id] = families[family_id] + 1
                i = i + 1
        print(i)
        print(families)

    def _get_top_family(self, person, family_id):
        parent_family_id = family_id
        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self.db.get_family_from_handle(family_handle)
            parent_family_id = family.gramps_id
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            parent_handle = father_handle if father_handle else mother_handle
            if parent_handle:
                parent = self.db.get_person_from_handle(parent_handle)
                name = person.get_primary_name()
                first_name = name.first_name
                surname = name.get_surname()
                parent_family_id = self._get_top_family(parent, parent_family_id)
        return parent_family_id
