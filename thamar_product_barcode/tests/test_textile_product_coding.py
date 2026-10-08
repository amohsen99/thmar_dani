# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestTextileProductCoding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.yarn_category = cls.env["product.category"].create({
            "name": "Test yarn polyester",
            "product_code_scheme": "serial",
            "product_code_prefix": "0101",
            "product_code_serial_digits": 4,
        })

    def test_serial_code_for_yarn(self):
        first = self.env["product.template"].create({
            "name": "Test yarn one",
            "categ_id": self.yarn_category.id,
        })
        second = self.env["product.template"].create({
            "name": "Test yarn two",
            "categ_id": self.yarn_category.id,
        })

        self.assertEqual(first.product_variant_id.default_code, "01010001")
        self.assertEqual(first.product_variant_id.barcode, "01010001")
        self.assertEqual(second.product_variant_id.default_code, "01010002")

    def test_finished_fabric_uses_grade_and_design_variant(self):
        grade = self.env["product.attribute"].create({
            "name": "Test quality grade",
            "create_variant": "always",
            "textile_code_role": "grade",
            "value_ids": [
                (0, 0, {"name": "First", "textile_code": "1"}),
                (0, 0, {"name": "Second", "textile_code": "2"}),
            ],
        })
        design = self.env["product.attribute"].create({
            "name": "Test design",
            "create_variant": "always",
            "textile_code_role": "design",
            "value_ids": [
                (0, 0, {"name": "Design 1", "textile_code": "0001"}),
                (0, 0, {"name": "Design 2", "textile_code": "0002"}),
            ],
        })
        category = self.env["product.category"].create({
            "name": "Test printed polyester",
            "product_code_scheme": "serial",
            "product_code_prefix": "311",
            "product_code_serial_digits": 4,
            "product_code_variant_source": "design",
            "product_code_grade_position": "before_serial",
        })
        template = self.env["product.template"].create({
            "name": "Test printed fabric",
            "categ_id": category.id,
            "attribute_line_ids": [
                (0, 0, {"attribute_id": grade.id, "value_ids": [(6, 0, grade.value_ids.ids)]}),
                (0, 0, {"attribute_id": design.id, "value_ids": [(6, 0, design.value_ids.ids)]}),
            ],
        })

        self.assertEqual(template.product_code_serial, "0001")
        self.assertEqual(
            set(template.product_variant_ids.mapped("default_code")),
            {"311100010001", "311100010002", "311200010001", "311200010002"},
        )
        self.assertEqual(
            set(template.product_variant_ids.mapped("barcode")),
            set(template.product_variant_ids.mapped("default_code")),
        )

    def test_fixed_code_rejects_second_product(self):
        category = self.env["product.category"].create({
            "name": "Test printing residue",
            "product_code_scheme": "fixed",
            "product_code_fixed_value": "3555555",
        })
        self.env["product.template"].create({
            "name": "Test printing residue one",
            "categ_id": category.id,
        })

        with self.assertRaises(ValidationError):
            self.env["product.template"].create({
                "name": "Test printing residue two",
                "categ_id": category.id,
            })

    def test_coding_category_is_locked_after_serial_reservation(self):
        self.env["product.template"].create({
            "name": "Test locked coding category",
            "categ_id": self.yarn_category.id,
        })

        with self.assertRaises(ValidationError):
            self.yarn_category.write({"product_code_prefix": "0199"})
