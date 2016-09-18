# -*- coding: utf-8 -*-
# Copyright 2016 Therp BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import date
from dateutil.relativedelta import relativedelta

from openerp import fields
from openerp.exceptions import ValidationError

from .test_partner_relation_common import TestPartnerRelationCommon


class TestPartnerRelation(TestPartnerRelationCommon):

    def test_selection_name_search(self):
        """Test wether we can find type selection on reverse name."""
        selection_types = self.selection_model.name_search(
            name=self.selection_person2company.name
        )
        self.assertTrue(selection_types)
        self.assertTrue(
            (self.selection_person2company.id,
             self.selection_person2company.name) in selection_types
        )

    def test_self_allowed(self):
        """Test creation of relation to same partner when type allows."""
        type_allow = self.type_model.create({
            'name': 'allow',
            'name_inverse': 'allow_inverse',
            'contact_type_left': 'p',
            'contact_type_right': 'p',
            'allow_self': True
        })
        self.assertTrue(type_allow)
        reflexive_relation = self.relation_model.create({
            'type_id': type_allow.id,
            'left_partner_id': self.partner_01_person.id,
            'right_partner_id': self.partner_01_person.id,
        })
        self.assertTrue(reflexive_relation)

    def test_self_disallowed(self):
        """Test creating relation to same partner when disallowed.

        Attempt to create a relation of a partner to the same partner should
        raise an error when the type of relation explicitly disallows this.
        """
        type_disallow = self.type_model.create({
            'name': 'disallow',
            'name_inverse': 'disallow_inverse',
            'contact_type_left': 'p',
            'contact_type_right': 'p',
            'allow_self': False
        })
        self.assertTrue(type_disallow)
        with self.assertRaises(ValidationError):
            self.relation_model.create({
                'type_id': type_disallow.id,
                'left_partner_id': self.partner_01_person.id,
                'right_partner_id': self.partner_01_person.id,
            })

    def test_self_default(self):
        """Test default not to allow relation with same partner.

        Attempt to create a relation of a partner to the same partner
        raise an error when the type of relation does not explicitly allow
        this.
        """
        type_default = self.type_model.create({
            'name': 'default',
            'name_inverse': 'default_inverse',
            'contact_type_left': 'p',
            'contact_type_right': 'p',
        })
        self.assertTrue(type_default)
        with self.assertRaises(ValidationError):
            self.relation_model.create({
                'type_id': type_default.id,
                'left_partner_id': self.partner_01_person.id,
                'right_partner_id': self.partner_01_person.id,
            })

    def test_self_mixed(self):
        """Test creation of relation with wrong types.

        Trying to create a relation between partners with an inappropiate
        type should raise an error.
        """
        with self.assertRaises(ValidationError):
            self.relation_model.create({
                'type_id': self.type_company2person.id,
                'left_partner_id': self.partner_01_person.id,
                'right_partner_id': self.partner_02_company.id,
            })

    def test_symmetric(self):
        """Test creating symmetric relation."""
        # Start out with non symmetric relation:
        type_symmetric = self.type_model.create({
            'name': 'not yet symmetric',
            'name_inverse': 'the other side of not symmetric',
            'is_symmetric': False,
            'contact_type_left': False,
            'contact_type_right': 'p',
        })
        # not yet symmetric relation should result in two records in
        # selection:
        selection_symmetric = self.selection_model.search([
            ('type_id', '=', type_symmetric.id),
        ])
        self.assertEqual(len(selection_symmetric), 2)
        # Now change to symmetric and test name and inverse name:
        with self.env.do_in_draft():
            type_symmetric.write(
                vals={
                    'name': 'sym',
                    'is_symmetric': True,
                }
            )
        with self.env.do_in_onchange():
            type_symmetric.onchange_is_symmetric()
        self.assertEqual(type_symmetric.is_symmetric, True)
        self.assertEqual(
            type_symmetric.name_inverse,
            type_symmetric.name
        )
        self.assertEqual(
            type_symmetric.contact_type_right,
            type_symmetric.contact_type_left
        )
        # now update the database:
        type_symmetric.write(
            vals={
                'name': type_symmetric.name,
                'is_symmetric': type_symmetric.is_symmetric,
                'name_inverse': type_symmetric.name_inverse,
                'contact_type_right': type_symmetric.contact_type_right,
            }
        )
        # symmetric relation should result in only one record in
        # selection:
        selection_symmetric = self.selection_model.search([
            ('type_id', '=', type_symmetric.id),
        ])
        self.assertEqual(len(selection_symmetric), 1)
        relation = self.relation_all_model.create({
            'type_selection_id': selection_symmetric.id,
            'this_partner_id': self.partner_02_company.id,
            'other_partner_id': self.partner_01_person.id,
        })
        partners = self.partner_model.search([
            ('search_relation_type_id', '=', relation.type_selection_id.id)
        ])
        self.assertTrue(self.partner_01_person in partners)
        self.assertTrue(self.partner_02_company in partners)

    def test_category_domain(self):
        """Test check on category in relations."""
        # Check on left side:
        with self.assertRaises(ValidationError):
            self.relation_model.create({
                'type_id': self.type_ngo2volunteer.id,
                'left_partner_id': self.partner_02_company.id,
                'right_partner_id': self.partner_04_volunteer.id,
            })
        # Check on right side:
        with self.assertRaises(ValidationError):
            self.relation_model.create({
                'type_id': self.type_ngo2volunteer.id,
                'left_partner_id': self.partner_03_ngo.id,
                'right_partner_id': self.partner_01_person.id,
            })

    def test_relation_type_change(self):
        """Test change in relation type conditions."""
        # First create a relation type having no particular conditions.
        (type_school2student,
         school2student,
         school2student_inverse) = (
            self._create_relation_type_selection({
                'name': 'school has student',
                'name_inverse': 'studies at school',
            })
        )
        # Second create relations based on those conditions.
        partner_school = self.partner_model.create({
            'name': 'Test School',
            'is_company': True,
            'ref': 'TS',
        })
        partner_bart = self.partner_model.create({
            'name': 'Bart Simpson',
            'is_company': False,
            'ref': 'BS',
        })
        partner_lisa = self.partner_model.create({
            'name': 'Lisa Simpson',
            'is_company': False,
            'ref': 'LS',
        })
        relation_school2bart = self.relation_all_model.create({
            'this_partner_id': partner_school.id,
            'type_selection_id': school2student.id,
            'other_partner_id': partner_bart.id,
        })
        self.assertTrue(relation_school2bart)
        relation_school2lisa = self.relation_all_model.create({
            'this_partner_id': partner_school.id,
            'type_selection_id': school2student.id,
            'other_partner_id': partner_lisa.id,
        })
        self.assertTrue(relation_school2lisa)
        relation_bart2lisa = self.relation_all_model.create({
            'this_partner_id': partner_bart.id,
            'type_selection_id': school2student.id,
            'other_partner_id': partner_lisa.id,
        })
        self.assertTrue(relation_bart2lisa)
        # Third creata a category and make it a condition for the
        #     relation type.
        # - Test restriction
        # - Test ignore
        category_student = self.category_model.create({
            'name': 'Student',
        })
        with self.assertRaises(ValidationError):
            type_school2student.write({
                'partner_category_right': category_student.id,
            })
        self.assertFalse(type_school2student.partner_category_right.id)
        type_school2student.write({
            'handle_invalid_onchange': 'ignore',
            'partner_category_right': category_student.id,
        })
        self.assertEqual(
            type_school2student.partner_category_right.id,
            category_student.id
        )
        # Fourth make company type a condition for left partner
        # - Test ending
        # - Test deletion
        partner_bart.write({
            'category_id': [(4, category_student.id)],
        })
        partner_lisa.write({
            'category_id': [(4, category_student.id)],
        })
        # Future student to be deleted by end action:
        partner_homer = self.partner_model.create({
            'name': 'Homer Simpson',
            'is_company': False,
            'ref': 'HS',
            'category_id': [(4, category_student.id)],
        })
        relation_lisa2homer = self.relation_all_model.create({
            'this_partner_id': partner_lisa.id,
            'type_selection_id': school2student.id,
            'other_partner_id': partner_homer.id,
            'date_start': fields.Date.to_string(
                date.today() + relativedelta(months=+6)
            ),
        })
        self.assertTrue(relation_lisa2homer)
        type_school2student.write({
            'handle_invalid_onchange': 'end',
            'contact_type_left': 'c',
        })
        self.assertEqual(
            relation_bart2lisa.date_end,
            fields.Date.today()
        )
        self.assertFalse(relation_lisa2homer.exists())
        type_school2student.write({
            'handle_invalid_onchange': 'delete',
            'contact_type_left': 'c',
            'contact_type_right': 'p',
        })
        self.assertFalse(relation_bart2lisa.exists())