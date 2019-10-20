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
import logging
from datetime import date, timedelta
from gramps.gen.plug.docgen import BaseDoc, TextDoc
from gramps.gen.plug.docbackend import DocBackend
from gramps.gen.plug import docgen
from gramps.gen.plug.menu import PersonOption
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.lib.eventtype import EventType
from gramps.gen.lib.notetype import NoteType
from gramps.gen.lib.person import Person
from gramps.gen.lib.note import Note
from gramps.gen.lib.date import Date as GrampsDate
LOG = logging.getLogger(".Chronicles")


BORN_SYMBOL = r"\gtrsymBorn"
BAPTIZED_SYMBOL = r"\gtrsymBaptized"
DIED_SYMBOL = r"\gtrsymDied"
BURIAL_SYMBOL = r"\gtrsymBuried"
MARRIED_SYMBOL = r"\gtrsymMarried"
ENGAGED_SYMBOL = r"\gtrsymEngaged"

# BORN_SYMBOL = "b"
# DIED_SYMBOL = "d"
# MARRIED_SYMBOL = "m"

class FamilyChronicles(Report):
    """
    Condensed family report suitable for family chronicles.
    """
    def __init__(self, database, options, user):
        # Inject simplified LaTeX handler
        options.set_document(
            SimpleLaTeXDoc(
                options.handler.doc.get_style_sheet(),
                options.handler.doc.paper, [])
        )
        Report.__init__(self, database, options, user)
        menu = options.menu
        self.person_id = menu.get_option_by_name('pid').get_value()
        self._person_id_list = []
        self._person_appearance_list = []

    def begin_report(self):
        """
        Collect all persons and order them by earliest event date
        """
        self._person_id_list = []
        self._person_appearance_list = []
        main_person = self.database.get_person_from_gramps_id(self.person_id)
        self._collect_persons(main_person)
        sorted_idx = \
            [i[0] for i in sorted(enumerate(self._person_appearance_list), \
                key=lambda x: x[1])]
        self._person_id_list = [self._person_id_list[i] for i in sorted_idx]

    def _collect_persons(self, person):
        earliest_date = self._get_earliest_event_date(person)
        generation_offset = (earliest_date is None)
        children_count = 0
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            if family.get_father_handle() == person.handle:
                earliest_family_date = \
                    self._get_earliest_event_date(family, generation_offset)
                if earliest_date:
                    if earliest_family_date \
                        and earliest_date > earliest_family_date:
                        earliest_date = earliest_family_date
                else:
                    earliest_date = earliest_family_date

                children_count += len(family.get_child_ref_list())
                for child_ref in family.get_child_ref_list():
                    child = self.database.get_person_from_handle(child_ref.ref)
                    earliest_child_date = \
                        self._get_earliest_event_date(child, generation_offset)
                    if earliest_date:
                        if earliest_child_date \
                            and earliest_date > earliest_child_date:
                            earliest_date = earliest_child_date
                    else:
                        earliest_date = earliest_child_date
                    self._collect_persons(child)

        if not earliest_date:
            earliest_date = date(2999, 12, 31)
        if children_count > 0:
            self._person_id_list.append(person.gramps_id)
            self._person_appearance_list.append(earliest_date)

    def _get_earliest_event_date(self, person, generation_offset=False):
        earliest_date = None
        for event_ref in person.get_event_ref_list():
            event = self.database.get_event_from_handle(event_ref.ref)
            date_object = event.get_date_object()
            if date_object:
                date_components = date_object.get_dmy()
                if date_components[2] > 0:
                    date_components = (
                        max(date_components[0], 1),
                        max(date_components[1], 1),
                        date_components[2])
                    event_date = date(
                        year=date_components[2],
                        month=date_components[1],
                        day=date_components[0])
                    if not earliest_date or earliest_date > event_date:
                        earliest_date = event_date
        if earliest_date and generation_offset:
            earliest_date -= timedelta(days=20*365)
        return earliest_date

    def write_report(self):
        for person_id in self._person_id_list:
            person = self.database.get_person_from_gramps_id(person_id)
            self.__write_person(person)

    def __write_person(self, person):
        self.doc.start_table('myTable', 'Family-Table')

        for fam_idx, family_handle in \
            enumerate(person.get_family_handle_list()):
            family = self.database.get_family_from_handle(family_handle)

            mother_handle = family.get_mother_handle()
            mother = self.database.get_person_from_handle(mother_handle)
            marriage_ref = self.__get_marriage_event_ref(family)

            if fam_idx == 0:
                father_handle = family.get_father_handle()
                father = self.database.get_person_from_handle(father_handle)
                self.__write_parent(father)
                self.__write_parent_family(father)
                # self._write_background_info(father)
            else:
                self.doc.start_row()
                self.doc.start_cell('Family-Cell')
                self.doc.write_text("{}. Ehe".format(fam_idx+1))
                self.doc.end_cell()
                self.doc.start_cell('Family-Cell', 14)
                self.doc.end_cell()
                self.doc.end_row()

            self.__write_parent(mother, marriage_ref)
            # self.__write_parent2(mother, marriage_ref, mother_heimatort)
            #self.__write_parent_of(mother)
            self.doc.write_text(r"\\"+"\n")

            do_person_report = len(family.get_child_ref_list()) * [False]
            for idx, child_ref in enumerate(family.get_child_ref_list()):
                child = self.database.get_person_from_handle(child_ref.ref)
                do_person_report[idx] = self.__write_child(child)

            if fam_idx < len(person.get_family_handle_list()):
                self.doc.write_text(r"\\"+"\n"+r"\\"+"\n"+r"\\"+"\n"+r"\\"+"\n")

        self.doc.end_table(person.gramps_id)

    def __write_basic_person(self, person, full_name=True,
                             is_main_person=False):
        name = self.__get_simple_name(person)

        birth_data = {'sym':'', 'date':'', 'loc':''}
        death_data = {'sym':'', 'date':'', 'loc':''}
        heimatort_data = {'sym':'', 'date':'', 'loc':''}

        for event_ref in person.get_event_ref_list():
            (event_type, event_date, event_place, _) = \
                self.__get_simple_event(event_ref)
            if event_type.is_birth():
                birth_data['sym'] = BORN_SYMBOL
                birth_data['date'] = event_date
                if event_place:
                    birth_data['loc'] = event_place
            elif event_type.is_baptism():
                if not birth_data['sym']:
                    birth_data['sym'] = BAPTIZED_SYMBOL
                    birth_data['date'] = event_date
                if not birth_data['loc'] and event_place:
                    birth_data['loc'] = event_place

            if event_type.is_death():
                death_data['sym'] = DIED_SYMBOL
                death_data['date'] = event_date
                if event_place:
                    death_data['loc'] = event_place
            elif event_type.is_burial():
                if not death_data['sym']:
                    death_data['sym'] = BURIAL_SYMBOL
                    death_data['date'] = event_date
                if not birth_data['loc'] and event_place:
                    death_data['loc'] = event_place

            if event_type.is_type('Census'):
                if event_place:
                    heimatort_data['loc'] = event_place

        self.doc.start_cell('Family-Cell')
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

        self.doc.start_cell('Family-Cell')
        self.doc.write_text(birth_data['sym'])
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        self.doc.write_text(birth_data['date'])
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        self.doc.write_text(birth_data['loc'])
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        if death_data['date']:
            self.doc.write_text(death_data['sym'])
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        self.doc.write_text(death_data['date'])
        self.doc.end_cell()

        self.doc.start_cell('Family-Cell')
        self.doc.write_text(death_data['loc'])
        self.doc.end_cell()

    def __write_parent(self, person, marriage_ref=None):
        note_list = []
        for ref_handle in person.get_referenced_handles():
            if ref_handle[0] == Note.__name__:
                note = self.database.get_note_from_handle(ref_handle[1])
                if note.get_type() == NoteType.PERSON:
                    note_list.append(note.get())

        if not note_list:
            vocation_list = set()
            for event_ref in person.get_event_ref_list():
                event = self.database.get_event_from_handle(event_ref.ref)
                event_type = event.get_type()
                if event_type.value in \
                    (EventType.ELECTED, EventType.OCCUPATION):
                    vocation_list.add(event.get_description())
            if vocation_list:
                note_list.append(", ".join(list(vocation_list)))

        if marriage_ref:
            heimatort_ref = self.__get_heimatort_event_ref(person)
            (_, _, parent_heimatort, _) = self.__get_simple_event(heimatort_ref)
            marriage_line = 1
        else:
            marriage_line = 0

        number_of_lines = max(1, marriage_line + len(note_list))
        for line_idx in range(number_of_lines):
            self.doc.start_row()
            if line_idx == 0:
                # 8 cells
                self.__write_basic_person(
                    person,
                    is_main_person=(marriage_ref is None))
            else:
                self.doc.start_cell('Family-Cell', 8)
                self.doc.end_cell()
            self.doc.start_cell('Family-Cell')
            self.doc.end_cell()
            if marriage_ref and line_idx == 0:
                # 3 cells
                self.__write_marriage(marriage_ref, True)

                self.doc.start_cell('Family-Cell')
                if parent_heimatort:
                    self.doc.write_text("v. {}".format(parent_heimatort))
                self.doc.end_cell()

                self.doc.start_cell('Family-Cell', 2)
                self.doc.end_cell()
            else:
                self.doc.start_cell('Family-Cell', 6, 'N')
                if note_list:
                    self.doc.write_text(note_list[line_idx - marriage_line])
                self.doc.end_cell()
            self.doc.end_row()

    def __write_parent_family(self, person):
        family_handle = person.get_parent_family_handle_list()
        father = None
        mother = None

        parent_names = []
        if family_handle:
            family = self.database.get_family_from_handle(family_handle[0])
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            parent_names = []
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                name = self.__get_simple_name(father)
                parent_names.append("{} {}".format(name[0], name[1]))
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                name = self.__get_simple_name(mother)
                parent_names.append("{} {}".format(name[0], name[1]))
        if person.get_gender() == Person.MALE:
            text = "Sohn von "
        elif person.get_gender() == Person.FEMALE:
            text = "Tochter von "
        else:
            text = "Kind von "

        if parent_names:
            self.doc.start_row()
            self.doc.start_cell('Family-Cell', 5)
            self.doc.write_text(text + " und ".join(parent_names))
            self.doc.end_cell()
            for _ in range(9):
                self.doc.start_cell('Family-Cell')
                self.doc.end_cell()
            self.doc.start_cell('Family-Cell')
            if father and father.gramps_id in self._person_id_list:
                self.doc.write_text("S. ")
                self.doc.make_pageref(father.gramps_id)
            elif mother and mother.gramps_id in self._person_id_list:
                self.doc.write_text("S. ")
                self.doc.make_pageref(mother.gramps_id)
            self.doc.end_cell()
            self.doc.end_row()


    # def __write_parent2(self, person, marriage_ref=None, heimatort=None,
    #                    is_main_person=False):
    #     note_list = []
    #     for ref_handle in person.get_referenced_handles():
    #         if ref_handle[0] == Note.__name__:
    #             note = self.database.get_note_from_handle(ref_handle[1])
    #             if note.get_type() == NoteType.PERSON:
    #                 note_list.append(note.get())

    #     if not note_list:
    #         vocation_list = set()
    #         for event_ref in person.get_event_ref_list():
    #             event = self.database.get_event_from_handle(event_ref.ref)
    #             event_type = event.get_type()
    #             if event_type.value in \
    #                 (EventType.ELECTED, EventType.OCCUPATION):
    #                 vocation_list.add(event.get_description())
    #         if vocation_list:
    #             note_list.append(", ".join(list(vocation_list)))


    #     self.doc.start_row()
    #     # 8 cells
    #     self.__write_basic_person(person, is_main_person=is_main_person)

    #     self.doc.start_cell('Family-Cell')
    #     self.doc.end_cell()

    #     self.__write_marriage(marriage_ref, True)

    #     self.doc.start_cell('Family-Cell')
    #     if heimatort:
    #         self.doc.write_text("v. {}".format(heimatort))
    #     self.doc.end_cell()

    #     self.doc.start_cell('Family-Cell', 2)
    #     self.doc.end_cell()

    #     self.doc.end_row()

    # def _write_background_info(self, person):
    #     family_handle = person.get_parent_family_handle_list()
    #     father_name = ["?", ""]
    #     mother_name = ["?", ""]

    #     if family_handle:
    #         family = self.database.get_family_from_handle(family_handle[0])
    #         father_handle = family.get_father_handle()
    #         mother_handle = family.get_mother_handle()
    #         if father_handle:
    #             father_name = self.__get_simple_name(
    #                 self.database.get_person_from_handle(father_handle)
    #             )
    #         if mother_handle:
    #             mother_name = self.__get_simple_name(
    #                 self.database.get_person_from_handle(mother_handle)
    #             )
    #     parent_names = "{} {} und {} {}".format(
    #         father_name[0], father_name[1], mother_name[0], mother_name[1]
    #     )

    #     note_list = []
    #     for ref_handle in person.get_referenced_handles():
    #         if ref_handle[0] == Note.__name__:
    #             note = self.database.get_note_from_handle(ref_handle[1])
    #             if note.get_type() == NoteType.PERSON:
    #                 note_list.append(note.get())

    #     if not note_list:
    #         vocation_list = set()
    #         for event_ref in person.get_event_ref_list():
    #             event = self.database.get_event_from_handle(event_ref.ref)
    #             event_type = event.get_type()
    #             if event_type.value in \
    #                 (EventType.ELECTED, EventType.OCCUPATION):
    #                 vocation_list.add(event.get_description())
    #         if vocation_list:
    #             note_list.append(", ".join(list(vocation_list)))

    #     background_lines = max(1, len(note_list))
    #     if person.get_gender() == Person.MALE:
    #         text = "Sohn von "
    #     elif person.get_gender() == Person.FEMALE:
    #         text = "Tochter von "
    #     else:
    #         text = "Kind von "

    #     for background_line_idx in range(background_lines):
    #         self.doc.start_row()
    #         self.doc.start_cell('Family-Cell', 5)
    #         # if background_line_idx == 0:
    #         #     self.doc.write_text(
    #         #         r"\multirow{" + str(background_lines) + "}{*}{" \
    #         #             + text + parent_names + "}")
    #         self.doc.end_cell()
    #         self.doc.start_cell('Family-Cell', 4)
    #         self.doc.end_cell()
    #         self.doc.start_cell('Family-Cell', 5)
    #         if note_list:
    #             self.doc.write_text(note_list[background_line_idx])
    #         self.doc.end_cell()
    #         self.doc.start_cell('Family-Cell')
    #         if background_line_idx == 0:
    #             self.doc.write_text("S. 000")
    #         self.doc.end_cell()
    #         self.doc.end_row()

    def __write_child(self, person):
        self.doc.start_row()
        # 8 cells
        self.__write_basic_person(person, full_name=False)
        followup = True

        family_handle_list = person.get_family_handle_list()
        if not family_handle_list:
            self.doc.start_cell('Family-Cell', 7)
            self.doc.end_cell()
            self.doc.end_row()
            followup = False
        else:
            for idx, family_handle in enumerate(family_handle_list):
                if idx > 0:
                    self.doc.start_row()
                    #no basic person
                    self.doc.start_cell('Family-Cell', 8)
                    self.doc.end_cell()

                family = self.database.get_family_from_handle(family_handle)
                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()
                if father_handle == person.handle:
                    spouse_handle = mother_handle
                else:
                    spouse_handle = father_handle
                if spouse_handle:
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    spouse_name = self.__get_simple_name(spouse)
                    spouse_heimatort_ref = \
                        self.__get_heimatort_event_ref(spouse)
                    if spouse_heimatort_ref:
                        (_, _, spouse_heimatort, _) = \
                            self.__get_simple_event(spouse_heimatort_ref)
                    else:
                        spouse_heimatort = ''
                marriage_ref = self.__get_marriage_event_ref(family)

                self.doc.start_cell('Family-Cell')
                self.doc.end_cell()

                # 2 cells
                self.__write_marriage(marriage_ref)

                if spouse_handle:
                    self.doc.start_cell('Family-Cell')
                    self.doc.write_text(
                        "{} {} ".format(spouse_name[0], spouse_name[1]))
                    self.doc.end_cell()

                    self.doc.start_cell('Family-Cell')
                    if spouse_heimatort:
                        self.doc.write_text("v. {}".format(spouse_heimatort))
                    self.doc.end_cell()
                else:
                    self.doc.start_cell('Family-Cell', 2)
                    self.doc.end_cell()


                self.doc.start_cell('Family-Cell')
                self.doc.end_cell()
                self.doc.start_cell('Family-Cell')
                if person.gramps_id in self._person_id_list:
                    self.doc.write_text("S. ")
                    self.doc.make_pageref(person.gramps_id)
                self.doc.end_cell()

                self.doc.end_row()
                followup = (father_handle == person.handle)

        return followup

    def __write_marriage(self, marriage_ref, show_place=False):
        if marriage_ref:
            (marriage_type, marriage_date, marriage_place, _) = \
                self.__get_simple_event(marriage_ref)
            self.doc.start_cell('Family-Cell')
            if marriage_type:
                if marriage_type.is_marriage():
                    symbol = MARRIED_SYMBOL
                elif marriage_type.is_marriage_fallback():
                    symbol = ENGAGED_SYMBOL
                else:
                    symbol = "?"
                self.doc.write_text(symbol)
            else:
                # default, in case only spouse is known
                self.doc.write_text(MARRIED_SYMBOL)
            self.doc.end_cell()

            self.doc.start_cell('Family-Cell')
            self.doc.write_text(marriage_date)
            self.doc.end_cell()

            if show_place:
                self.doc.start_cell('Family-Cell')
                self.doc.write_text(marriage_place)
                self.doc.end_cell()
        else:
            self.doc.start_cell('Family-Cell')
            self.doc.end_cell()
            self.doc.start_cell('Family-Cell')
            self.doc.end_cell()
            if show_place:
                self.doc.start_cell('Family-Cell')
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
            date_text = self._get_date_text(event_date)
            # date_text = datehandler.displayer.display(event_date)
            place_handle = event.get_place_handle()
            description = event.get_description()
            event_type = event.get_type()
        else:
            date_text = ""
            event_type = None
            description = ""

        if event_ref and place_handle:
            place = self.database.get_place_from_handle(place_handle)
            place_text = place_displayer.display(
                self.database, place, event_date)
        else:
            place_text = ""

        return event_type, date_text, place_text, description

    def _get_date_text(self, date_obj):
        date_text = ""
        if date_obj.get_modifier() == GrampsDate.MOD_NONE:
            if date_obj.dateval[0] == 0:
                if date_obj.dateval[1] == 0:
                    if date_obj.dateval[2] == 0:
                        date_text = ""
                    else:
                        date_text = "{}".format(date_obj.dateval[2])
                else:
                    date_text = "{}.{}".format(date_obj.dateval[1], date_obj.dateval[2])
            else:
                date_text = "{}.{}.{}".format(
                    date_obj.dateval[0],
                    date_obj.dateval[1],
                    date_obj.dateval[2])
        # if date_obj.get_modifier() == GrampsDate.MOD_BEFORE:
        #     date_text = "vor " + date_text
        # elif date_obj.get_modifier() == GrampsDate.MOD_AFTER:
        #     date_text = "nach " + date_text
        return date_text

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

        table = docgen.TableStyle()
        table.set_width(100)
        table.set_columns(15)
        table.set_column_width(0, 7)
        table.set_column_width(1, 7)
        table.set_column_width(2, 6)
        table.set_column_width(3, 7)
        table.set_column_width(4, 7)
        table.set_column_width(5, 6)
        table.set_column_width(6, 7)
        table.set_column_width(7, 7)
        table.set_column_width(8, 6)
        table.set_column_width(9, 7)
        table.set_column_width(10, 7)
        table.set_column_width(11, 6)
        table.set_column_width(12, 7)
        table.set_column_width(13, 7)
        table.set_column_width(14, 6)
        default_style.add_table_style('Family-Table', table)


        cell = docgen.TableCellStyle()
        default_style.add_cell_style('Family-Cell', cell)

class SimpleLaTeXDoc(BaseDoc, TextDoc):
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
        self._backend = DocBackend(filename)
        self._backend.open()
        # self._backend.write(
        #     r"\documentclass[a4paper,landscape,10pt]{article}" + "\n")
        self._backend.write(r"\documentclass[10pt]{extarticle}" + "\n")
        self._backend.write(r"\usepackage[a4paper,landscape,left=2cm]{geometry}" + "\n")
        self._backend.write(r"\usepackage{multirow}" + "\n")
        self._backend.write(r"\usepackage{array}" + "\n")
        self._backend.write(r"\usepackage{calc}" + "\n")
        self._backend.write(r"\usepackage{genealogytree}" + "\n")
        self._backend.write(r"\newcommand{\namewidth}{0.15\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\locationwidth}{0.09\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\datewidth}{0.07\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\symbolwidth}{0.005\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\referencewidth}{0.04\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\heimatortwidth}{0.12\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\gapwidth}{0.01\textwidth}" + "\n")
        self._backend.write(r"\newcommand{\notewidth}{\symbolwidth+\datewidth+\namewidth+\heimatortwidth}" + "\n")
        self._backend.write(r"\newcolumntype{N}{>{\raggedright\arraybackslash}p{\notewidth}}" + "\n")
        self._backend.write(r"\begin{document}" + "\n")
        self._backend.write(r"\newgeometry{left=1.5cm} % Ränder kleiner" + "\n")


    def close(self):
        """Clean up and close the document"""
        self._backend.write(r"\end{document}")
        self._backend.close()

    def write_text(self, text, mark=None, links=False):
        """Write the text to the file"""
        if self._open_cell is None:
            self._backend.write(text)
        else:
            self.__append_to_cell(text)

    def start_paragraph(self, style_name, leader=None):
        """Paragraphs handling - A Gramps paragraph is any
        single body of text from a single word to several sentences.
        We assume a linebreak at the end of each paragraph."""

    def end_paragraph(self):
        """End the current paragraph"""
        pass

    def start_bold(self):
        control = r"\textbf{"
        if self._open_cell is None:
            self._backend.write(control)
        else:
            self.__append_to_cell(control)

    def end_bold(self):
        """End bold face"""
        control = r"}"
        if self._open_cell is None:
            self._backend.write(control)
        else:
            self.__append_to_cell(control)

    def start_table(self, name, style_name):
        """Begin new table"""
        self._backend.write(r"\begin{table}" + "\n")
        self._backend.write(
            r"\begin{tabular}{" + "\n" + \
            r"p{\namewidth}" + "\n" + \
            r"p{\symbolwidth}" + "\n" + \
            r">{\raggedleft\arraybackslash}p{\datewidth}" + "\n" + \
            r"p{\locationwidth}" + "\n" + \
            r"p{\gapwidth}" + "\n" + \
            r">{\centering}p{\symbolwidth}" + "\n" + \
            r">{\raggedleft\arraybackslash}p{\datewidth}" + "\n" + \
            r"p{\locationwidth}" + "\n" + \
            r"p{\gapwidth}" + "\n" + \
            r">{\centering}p{\symbolwidth}" + "\n" + \
            r">{\raggedleft\arraybackslash}p{\datewidth}" + "\n" + \
            r"p{\namewidth}" + "\n" + \
            r"p{\heimatortwidth}" + "\n" + \
            r"p{\gapwidth}" + "\n" + \
            r"p{\referencewidth}" + "\n" + \
            r"}" + "\n")

    def end_table(self, label=None):
        """Close the table environment"""
        self._backend.write(r"\end{tabular}" + "\n")
        if label:
            self.write_text(r"\label{" + label +"}")
        # self._backend.write(r"\vspace{3.6cm}" + "\n")
        # self._backend.write(r"\\\\\noindent\rule[0.6ex]{\linewidth}{1pt}" + "\n")
        self._backend.write(r"\end{table}" + "\n")

    def start_row(self):
        """Begin a new row"""
        self._table_cells = []

    def end_row(self):
        """End the row (new line)"""
        self._backend.write("&".join(self._table_cells))

        self._backend.write(r"\\" + "\n")

    def start_cell(self, style_name, span=1, format='l'):
        """Add an entry to the table.
        We always place our data inside braces
        for safety of formatting."""
        self._open_cell = ("", 1)
        # if span > 1:
        #     self._open_cell = (r"\multicolumn{" + \
        #                        "{}".format(span) + r"}{l}{", span)
        if span > 1:
            self._open_cell = (r"\multicolumn" + \
                "{{{}}}{{{}}}{{".format(span, format), span)


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

    def make_pageref(self, label):
        self.write_text(r"\pageref{" + label +"}")

    def __append_to_cell(self, text):
        self._open_cell = (self._open_cell[0] + text, self._open_cell[1])
