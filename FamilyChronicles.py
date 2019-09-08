#
# Gramps - a GTK+/GNOME based genealogy program - Family Summary plugin
#
# Copyright (C) 2008,2009,2010 Reinhard Mueller
# Copyright (C) 2010 Jakim Friant
# Copyright (C) 2016 Serge Noiraud
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

# $Id$

"""Reports/Text Reports/Family Chronicles"""
from gramps.gen.plug.menu import PersonOption

from gramps.gen.plug import docgen
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen import datehandler
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.lib.eventtype import EventType

class FamilyChronicles(Report):
    """
    Condensed family report suitable for family chronicles.
    """
    def __init__(self, database, options, user):
        Report.__init__(self, database, options, user)
        menu = options.menu
        self.person_id = menu.get_option_by_name('pid').get_value()

    def write_report(self):
        person = self.database.get_person_from_gramps_id(self.person_id)
        self.__write_person_report(person)

    def __write_person_report(self, person):
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            self.__write_family(family)


    def __write_family(self, family):
        self.doc.start_table('myTable', 'family_table')
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        father = self.database.get_person_from_handle(father_handle)
        mother = self.database.get_person_from_handle(mother_handle)
        heimatort_ref = self.__get_heimatort_event_ref(mother)
        (_, _, mother_heimatort) = self.__get_simple_event(heimatort_ref)
        marriage_ref = self.__get_marriage_event_ref(family)

        self.__write_parent(father, is_main_person=True)
        self.__write_parent_of(father)
        self.__write_parent(mother, marriage_ref, mother_heimatort)
        self.__write_parent_of(mother)
        self.doc.write_text(r"\\"+"\n")

        do_person_report = len(family.get_child_ref_list()) * [False]
        for idx, child_ref in enumerate(family.get_child_ref_list()):
            child = self.database.get_person_from_handle(child_ref.ref)
            do_person_report[idx] = self.__write_child(child)
        self.doc.end_table()

        for idx, child_ref in enumerate(family.get_child_ref_list()):
            if do_person_report[idx]:
                child = self.database.get_person_from_handle(child_ref.ref)
                self.__write_person_report(child)

    def __write_basic_person(self, person, full_name=True,
                             is_main_person=False):
        name = self.__get_simple_name(person)

        (birth_type, birth_date, birth_place) = \
            self.__get_simple_event(person.get_birth_ref())
        (death_type, death_date, death_place) = \
            self.__get_simple_event(person.get_death_ref())

        self.doc.start_cell('family_cell')
        if is_main_person:
            self.doc.start_bold()
        if full_name:
            name_text = "{} {}".format(name[0], name[1])
        else:
            name_text = name[0]
        self.doc.write_text(name_text)
        if is_main_person:
            self.doc.end_bold()
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        if birth_type:
            self.doc.write_text(
                r"\gtrsymBorn" if birth_type.is_birth() else "?")
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.write_text(birth_date)
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.write_text(birth_place)
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        if death_type:
            self.doc.write_text(
                r"\gtrsymDied" if death_type.is_death() else "?")
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.write_text(death_date)
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.write_text(death_place)
        self.doc.end_cell()

    def __write_parent(self, person, marriage_ref=None, heimatort=None,
                       is_main_person=False):
        self.doc.start_row()
        # 8 cells
        self.__write_basic_person(person, is_main_person=is_main_person)

        self.doc.start_cell('family_cell')
        self.doc.end_cell()

        if marriage_ref:
            (marriage_type, marriage_date, marriage_place) = \
                self.__get_simple_event(marriage_ref)
            # 3 cells
            if not marriage_place:
                marriage_place = ""
            self.__write_marriage(marriage_type, marriage_date, marriage_place)
        else:
            self.doc.start_cell('family_cell', 3)
            self.doc.end_cell()

        self.doc.start_cell('family_cell')
        if heimatort:
            self.doc.write_text("von {}".format(heimatort))
        self.doc.end_cell()

        self.doc.start_cell('family_cell', 2)
        self.doc.end_cell()

        self.doc.end_row()

    def __write_parent_of(self, person):
        family_handle = person.get_parent_family_handle_list()
        father_name = ["?", ""]
        mother_name = ["?", ""]

        if family_handle:
            family = self.database.get_family_from_handle(family_handle[0])
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            if father_handle:
                father_name = self.__get_simple_name(
                    self.database.get_person_from_handle(father_handle)
                )
            if mother_handle:
                mother_name = self.__get_simple_name(
                    self.database.get_person_from_handle(mother_handle)
                )
        parent_names = "{} {} und {} {}".format(
            father_name[0], father_name[1], mother_name[0], mother_name[1]
        )
        self.doc.start_row()
        self.doc.start_cell('family_cell', 4)
        self.doc.write_text(parent_names)
        self.doc.end_cell()
        self.doc.start_cell('family_cell', 11)
        self.doc.end_cell()
        self.doc.end_row()


    def __write_child(self, person):
        self.doc.start_row()
        # 8 cells
        self.__write_basic_person(person, full_name=False)
        followup = True

        family_handle_list = person.get_family_handle_list()
        if not family_handle_list:
            self.doc.start_cell('family_cell', 7)
            self.doc.end_cell()
            self.doc.end_row()
            followup = False
        else:
            for idx, family_handle in enumerate(family_handle_list):
                if idx > 0:
                    self.doc.start_row()
                    #no basic person
                    self.doc.start_cell('family_cell', 8)
                    self.doc.end_cell()

                family = self.database.get_family_from_handle(family_handle)
                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()
                if father_handle == person.handle:
                    spouse_handle = mother_handle
                else:
                    spouse_handle = father_handle
                spouse = self.database.get_person_from_handle(spouse_handle)
                spouse_name = self.__get_simple_name(spouse)
                marriage_ref = self.__get_marriage_event_ref(family)
                (marriage_type, marriage_date, _) = \
                    self.__get_simple_event(marriage_ref)
                heimatort_ref = self.__get_heimatort_event_ref(spouse)
                (_, _, spouse_heimatort) = \
                    self.__get_simple_event(heimatort_ref)

                self.doc.start_cell('family_cell')
                self.doc.end_cell()

                # 2 cells
                self.__write_marriage(marriage_type, marriage_date)

                self.doc.start_cell('family_cell')
                if spouse_name:
                    self.doc.write_text(
                        "{} {}".format(spouse_name[0], spouse_name[1]))
                self.doc.end_cell()

                self.doc.start_cell('family_cell')
                if spouse_heimatort:
                    self.doc.write_text("von {}".format(spouse_heimatort))
                self.doc.end_cell()

                self.doc.start_cell('family_cell', 2)
                self.doc.end_cell()

                self.doc.end_row()
                followup = (father_handle == person.handle)

        return followup

    def __write_marriage(self, marriage_type,
                         marriage_date, marriage_place=None):
        self.doc.start_cell('family_cell')
        if marriage_type:
            self.doc.write_text(
                r"\gtrsymMarried" \
                    if marriage_type.is_marriage() else "?")
        else:
            # default, in case only spouse is known
            self.doc.write_text(r"\gtrsymMarried")
        self.doc.end_cell()

        self.doc.start_cell('family_cell')
        self.doc.write_text(marriage_date)
        self.doc.end_cell()

        if marriage_place is not None:
            self.doc.start_cell('family_cell')
            self.doc.write_text(marriage_place)
            self.doc.end_cell()

    def __get_simple_name(self, person):
        name = person.get_primary_name()
        first_name = name.first_name
        surname = name.get_surname()
        return (first_name, surname)

    def __get_simple_event(self, event_ref):
        if event_ref:
            event = self.database.get_event_from_handle(event_ref.ref)
            event_date = event.get_date_object()
            date_text = datehandler.displayer.display(event_date)
            place_handle = event.get_place_handle()
            event_type = event.get_type()
        else:
            date_text = ""
            event_type = None

        if event_ref and place_handle:
            place = self.database.get_place_from_handle(place_handle)
            place_text = place_displayer.display(
                self.database, place, event_date)
        else:
            place_text = ""

        return event_type, date_text, place_text

    def __get_marriage_event_ref(self, family):
        marriage_event_ref = None
        event_ref_list = family.get_event_ref_list()
        for event_ref in event_ref_list:
            event = self.database.get_event_from_handle(event_ref.ref)
            event_type = event.get_type()
            if event_type.is_marriage() or event_type.is_marriage_fallback():
                marriage_event_ref = event_ref
                break
        return marriage_event_ref

    def __get_heimatort_event_ref(self, person):
        heimatort_event_ref = None
        event_ref_list = person.get_event_ref_list()
        for event_ref in event_ref_list:
            event = self.database.get_event_from_handle(event_ref.ref)
            event_type = event.get_type()
            if event_type.value == EventType.CENSUS:
                heimatort_event_ref = event_ref
                break
        return heimatort_event_ref

class FamilyChroniclesOptions(MenuReportOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        category_name = "Report Options"
        self.__pid = PersonOption("Center person")
        self.__pid.set_help(
            "The person whose partners and children are printed")
        menu.add_option(category_name, "pid", self.__pid)

    def make_default_style(self, default_style):
        """Make default output style for the Family Sheet Report."""

        # font = docgen.FontStyle()
        # font.set_type_face(docgen.FONT_SANS_SERIF)
        # font.set_size(10)
        # font.set_bold(0)
        para = docgen.ParagraphStyle()
        # para.set_font(font)
        para.set_description("The basic style used for the text display")
        default_style.add_paragraph_style('normal', para)

        cell = docgen.TableCellStyle()
        default_style.add_cell_style('family_cell', cell)

        table = docgen.TableStyle()
        table.set_width(100)
        table.set_columns(15)
        table.set_column_width(0, 30)
        table.set_column_width(1, 30)
        table.set_column_width(2, 30)

        # table.set_column_width(0, 7)
        # table.set_column_width(1, 7)
        # table.set_column_width(2, 86)
        default_style.add_table_style('family_table', table)
